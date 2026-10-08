"""Campus Customs API: products, images, accounts, chat memory, safety, and the shop chatbot.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import append_record, new_run_id, now_iso, run_chat, short
from models import (
    ChatHistory, ChatReply, ChatRequest, ChatTurn, Customer, HistoryMessage, Product, ProductMatches, ShopDeps,
)
from tools import load_products


# ===========================================================================
# Accounts: password hashing, signed session cookies, auth routes
# ===========================================================================

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs.db"
load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256, salted, slow)
#
# Seed users use a legacy 3-part format:   pbkdf2_sha256$<salt>$<hex digest>        (120,000 iterations)
# New/upgraded users use a 4-part format:  pbkdf2_sha256$<iterations>$<salt>$<hex digest>
# The salt string's UTF-8 bytes are the PBKDF2 salt in both formats.
# ---------------------------------------------------------------------------
ALGO = "pbkdf2_sha256"
LEGACY_ITERATIONS = 120_000
ITERATIONS = 600_000  # OWASP 2023+ recommendation for PBKDF2-HMAC-SHA256


def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return f"{ALGO}${ITERATIONS}${salt}${_pbkdf2(password, salt, ITERATIONS)}"


def _parse(stored: str) -> tuple[int, str, str] | None:
    parts = stored.split("$")
    if len(parts) == 3 and parts[0] == ALGO:
        return LEGACY_ITERATIONS, parts[1], parts[2]
    if len(parts) == 4 and parts[0] == ALGO and parts[1].isdigit():
        return int(parts[1]), parts[2], parts[3]
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if not parsed:
        return False
    iterations, salt, digest = parsed
    return hmac.compare_digest(_pbkdf2(password, salt, iterations), digest)


def needs_rehash(stored: str) -> bool:
    parsed = _parse(stored)
    return parsed is None or parsed[0] < ITERATIONS


# A fixed dummy hash so unknown-email logins take as long as real ones (no account enumeration by timing).
_DUMMY_HASH = hash_password(secrets.token_hex(16))

# ---------------------------------------------------------------------------
# Sessions: HttpOnly cookie holding an HMAC-signed {user_id, exp}
# ---------------------------------------------------------------------------
COOKIE = "cc_session"
SESSION_SECONDS = 7 * 24 * 3600


def _secret() -> bytes:
    secret = os.getenv("SESSION_SECRET")
    if not secret:
        # Generate once and persist to .env so sessions survive restarts.
        secret = secrets.token_urlsafe(48)
        with open(ROOT / ".env", "a") as f:
            f.write(f"SESSION_SECRET={secret}\n")
        os.environ["SESSION_SECRET"] = secret
    return secret.encode()


def _sign(payload: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(_secret(), payload, "sha256").digest()).decode().rstrip("=")


def make_session_token(user_id: int) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"uid": user_id, "exp": int(time.time()) + SESSION_SECONDS}).encode()).decode().rstrip("=")
    return f"{payload}.{_sign(payload.encode())}"


def read_session_token(token: str | None) -> int | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, _sign(payload.encode())):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError:
        return None
    if data.get("exp", 0) < time.time():
        return None
    return int(data["uid"])


def _set_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE, make_session_token(user_id), max_age=SESSION_SECONDS,
        httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE") == "1", path="/",
    )

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def connect_rw() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


class PublicUser(BaseModel):
    """The only user fields ever sent to the browser (never the password hash)."""
    id: int
    first_name: str
    last_name: str
    name: str
    email: str


def _public(row: sqlite3.Row) -> PublicUser:
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return PublicUser(id=row["id"], first_name=first, last_name=last, name=row["name"], email=row["email"])


def get_user(user_id: int) -> PublicUser | None:
    con = connect_rw()
    try:
        row = con.execute("SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        con.close()
    return _public(row) if row else None


def get_customer(user_id: int) -> Customer | None:
    """Customer fields the chat agent may see (no password hash)."""
    con = connect_rw()
    try:
        row = con.execute("SELECT id, name, email, first_name, last_name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        con.close()
    if not row:
        return None
    u = _public(row)
    return Customer(user_id=u.id, first_name=u.first_name, last_name=u.last_name, email=u.email, member_since=row["created_at"][:10])


def current_user(request: Request) -> PublicUser | None:
    uid = read_session_token(request.cookies.get(COOKIE))
    return get_user(uid) if uid else None

# ---------------------------------------------------------------------------
# Simple brute-force protection: lock an email after repeated failures
# ---------------------------------------------------------------------------
MAX_FAILS, LOCK_SECONDS = 5, 15 * 60
_fails: dict[str, list[float]] = {}


def _locked(email: str) -> bool:
    recent = [t for t in _fails.get(email, []) if t > time.time() - LOCK_SECONDS]
    _fails[email] = recent
    return len(recent) >= MAX_FAILS

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _validate_password(pw: str) -> None:
    if len(pw) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")
    if len(pw) > 128:
        raise HTTPException(400, "Password must be at most 128 characters.")


@router.post("/signup", response_model=PublicUser, status_code=201)
def signup(body: SignupRequest, response: Response) -> PublicUser:
    first, last = body.first_name.strip(), body.last_name.strip()
    email = body.email.strip().lower()
    if not first or not last:
        raise HTTPException(400, "First and last name are required.")
    if len(first) > 50 or len(last) > 50:
        raise HTTPException(400, "Names must be 50 characters or fewer.")
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise HTTPException(400, "Please enter a valid email address.")
    _validate_password(body.password)
    if body.password != body.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    con = connect_rw()
    try:
        with con:
            cur = con.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        row = con.execute("SELECT id, name, email, first_name, last_name FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with that email already exists.")
    finally:
        con.close()
    _set_cookie(response, row["id"])
    return _public(row)


@router.post("/login", response_model=PublicUser)
def login(body: LoginRequest, response: Response) -> PublicUser:
    email = body.email.strip().lower()
    if _locked(email):
        raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")
    con = connect_rw()
    try:
        row = con.execute("SELECT id, name, email, first_name, last_name, password_hash FROM users WHERE lower(email) = ?", (email,)).fetchone()
        ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
        if not ok:
            _fails.setdefault(email, []).append(time.time())
            raise HTTPException(401, "Incorrect email or password.")
        _fails.pop(email, None)
        if needs_rehash(row["password_hash"]):
            # Upgrade legacy/weaker hashes to the current iteration count now that we know the password.
            with con:
                con.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(body.password), row["id"]))
    finally:
        con.close()
    _set_cookie(response, row["id"])
    return _public(row)


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(COOKIE, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=PublicUser | None)
def me(request: Request) -> PublicUser | None:
    return current_user(request)


# ===========================================================================
# Chat safety: redaction, rate limiting, crisis check
# ===========================================================================

CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PASSWORD_RE = re.compile(r"(?i)\b(pass(?:word|code|wd)?|pw)\b(\s*(?:is|:|=)\s*)(\S+)")


def _luhn_ok(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def redact(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, kinds_removed)."""
    removed: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            removed.append("card number")
            trailing = m.group(0)[len(m.group(0).rstrip(" -")):]
            return "[card number removed]" + trailing
        return m.group(0)

    text = CARD_RE.sub(card, text)
    if SSN_RE.search(text):
        removed.append("SSN")
        text = SSN_RE.sub("[SSN removed]", text)
    if PASSWORD_RE.search(text):
        removed.append("password")
        text = PASSWORD_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[password removed]", text)
    return text, sorted(set(removed))


class RateLimiter:
    """Sliding-window limiter: at most `limit` calls per `window` seconds per key (in memory)."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit, self.window = limit, window
        self.calls: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.calls[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


CHAT_LIMIT_PER_MINUTE = 12
chat_limiter = RateLimiter(CHAT_LIMIT_PER_MINUTE, 60.0)


# Messages that suggest the shopper may be in crisis get a caring, resource-first reply
# from the server (the model provider's filter would otherwise just block them).
CRISIS_RE = re.compile(
    r"(?i)\b(kill(ing)? myself|suicid\w*|end(ing)? my life|want(ed)? to die|don'?t want to (be here|live|exist)( anymore)?|"
    r"self[- ]?harm|hurt(ing)? myself|no reason to live)\b"
)
CRISIS_REPLY = (
    "I'm really sorry you're going through this, and I'm glad you said something. You don't have to handle it alone.\n\n"
    "- **Yale Mental Health & Counseling:** 203-432-0290 (24/7)\n"
    "- **988 Suicide & Crisis Lifeline:** call or text **988** (US)\n"
    "- **Emergency:** call **911**\n\n"
    "If you'd like, I'm still here to help with anything at the shop whenever you're ready."
)


def is_crisis(text: str) -> bool:
    return bool(CRISIS_RE.search(text))


# ===========================================================================
# Customer memory: chat history in the chat_messages table
# ===========================================================================

HISTORY_LIMIT = 50  # messages returned to the browser on reload
AGENT_CONTEXT_LIMIT = 12  # most recent messages replayed to the agent each turn


def save_turn(user_id: int, message: str, reply: ChatReply) -> None:
    """Store the shopper's message and the assistant's reply together (one transaction)."""
    matches_json = None
    if reply.matches:
        m = reply.matches
        matches_json = json.dumps({
            "title": m.title, "query": m.query, "total_matches": m.total_matches,
            "product_ids": [p.product_id for p in m.products],
        })
    con = connect_rw()
    try:
        with con:
            con.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
            con.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (user_id, reply.reply, matches_json or "[]"),
            )
    finally:
        con.close()


def _rows(user_id: int, limit: int) -> list[sqlite3.Row]:
    con = connect_rw()
    try:
        rows = con.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        con.close()
    return list(reversed(rows))  # oldest first; ordered by id because a turn's two rows share a timestamp


def _matches_from_json(raw: str | None, fallback_query: str) -> ProductMatches | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if isinstance(data, dict):
        ids, title, query, total = data.get("product_ids", []), data.get("title", ""), data.get("query", ""), data.get("total_matches")
    elif isinstance(data, list):  # legacy seed format: list of product snapshots
        ids, title, query, total = [p.get("product_id") for p in data if isinstance(p, dict)], "", "", None
    else:
        return None
    products = load_products([i for i in ids if isinstance(i, str)][:8])
    if not products:
        return None
    return ProductMatches(
        title=title or "Recommended for you", query=query or fallback_query,
        total_matches=max(total or 0, len(products)), products=products,
    )


def load_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[HistoryMessage]:
    """Saved turns for the chat widget, with product cards rebuilt from live data."""
    out: list[HistoryMessage] = []
    last_user_text = ""
    for r in _rows(user_id, limit):
        if r["role"] == "user":
            last_user_text = r["content"]
        out.append(HistoryMessage(
            role=r["role"], content=r["content"], created_at=r["created_at"].replace(" ", "T") + "Z",
            matches=_matches_from_json(r["products_json"], last_user_text) if r["role"] == "assistant" else None,
        ))
    return out


def agent_history(user_id: int) -> list[ChatTurn]:
    """Recent turns to replay to the agent (text only; prices and stock are always re-looked-up)."""
    return [ChatTurn(role=r["role"], content=r["content"][:4000]) for r in _rows(user_id, AGENT_CONTEXT_LIMIT)]


def clear_history(user_id: int) -> int:
    con = connect_rw()
    try:
        with con:
            return con.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
    finally:
        con.close()


# ===========================================================================
# FastAPI app and routes
# ===========================================================================

DATA_DIR = ROOT / "data"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)  # auth routes defined above

# Product images: catalogue.image_file_path "products/x.jpg" -> /media/products/x.jpg.
# Only the products folder is mounted, so the database file is never served.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/products", response_model=list[Product])
def list_products() -> list[Product]:
    return load_products()


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    found = load_products([product_id])
    if not found:
        raise HTTPException(404, "Product not found")
    return found[0]


@app.post("/api/chat", response_model=ChatReply)
async def chat(req: ChatRequest, request: Request) -> ChatReply:
    # Who the shopper is comes from the signed session cookie, never from the message.
    user = current_user(request)
    client = request.client.host if request.client else "unknown"
    if not chat_limiter.allow(f"user:{user.id}" if user else f"ip:{client}"):
        append_record({"time": now_iso(), "run_id": new_run_id(), "who": f"user:{user.id}" if user else "guest",
                       "page": req.page.path, "message": short(redact(req.message)[0], 200),
                       "stop_reason": "rate_limited", "steps": []})
        raise HTTPException(429, f"You're sending messages quickly. Please wait a moment (limit {CHAT_LIMIT_PER_MINUTE} per minute).")
    # Strip card numbers / SSNs / passwords before the text reaches the LLM or the database.
    message, removed = redact(req.message)
    if removed:
        message += f"\n\n[System note: the shopper's message contained a {', '.join(removed)}, which was removed for their safety. Remind them not to share it here; checkout isn't available in chat.]"
    customer = get_customer(user.id) if user else None
    if is_crisis(req.message):
        # Don't run the shopping agent; answer with support resources right away.
        append_record({"time": now_iso(), "run_id": new_run_id(), "who": f"user:{user.id}" if user else "guest",
                       "page": req.page.path, "message": "[withheld: wellbeing]", "stop_reason": "wellbeing_redirect", "steps": []})
        return ChatReply(reply=CRISIS_REPLY)
    # Logged-in shoppers: history comes from the database. Guests: from the browser (not saved).
    history = agent_history(customer.user_id) if customer else req.history
    deps = ShopDeps(customer=customer, page=req.page)
    try:
        reply = await run_chat(message, history, deps)
    except Exception:
        log.exception("Chat agent failed")
        raise HTTPException(502, "The shop assistant is having trouble right now. Please try again in a moment.")
    shown_message = redact(req.message)[0]
    if removed:
        reply.message_redacted = shown_message
    if customer:
        save_turn(customer.user_id, shown_message, reply)
    return reply


@app.get("/api/chat/history", response_model=ChatHistory)
def chat_history(request: Request) -> ChatHistory:
    """Saved conversation for the logged-in shopper (empty for guests)."""
    user = current_user(request)
    return ChatHistory(messages=load_history(user.id) if user else [])


@app.delete("/api/chat/history", status_code=204)
def delete_chat_history(request: Request) -> None:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Log in to manage saved chat history.")
    clear_history(user.id)
