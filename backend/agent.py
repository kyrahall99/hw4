"""Shop agent: model (OpenAI via Portkey), system prompt file, session context, tools,
output validators, loop limits, the chat entry point, and the append-only audit trail.
"""

import fcntl
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pathlib import Path
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart, UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits
from typing import Any

from models import AgentOutput, ChatReply, ChatTurn, ProductMatches, ShopDeps
from tools import TOOLS, category_of, load_products


# ===========================================================================
# Agent wiring
# ===========================================================================

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

PROMPT_PATH = HERE / "prompts" / "prompt.md"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.6-terra")
MAX_CARDS = 8

log = logging.getLogger("campus_customs.agent")


def build_model(model_name: str = CHAT_MODEL) -> OpenAIChatModel:
    """OpenAI-compatible chat model routed through the Portkey gateway."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing. Add it to the .env file in the project root.")
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key="portkey",  # unused by Portkey; auth is the header below
        default_headers={"x-portkey-api-key": api_key},
    )
    return OpenAIChatModel(model_name, provider=OpenAIProvider(openai_client=client))


shop_agent = Agent(
    build_model(),
    deps_type=ShopDeps,
    output_type=AgentOutput,
    instructions=PROMPT_PATH.read_text(encoding="utf-8"),
    tools=TOOLS,
    retries=2,
)


@shop_agent.instructions
def session_context(ctx: RunContext[ShopDeps]) -> str:
    """Per-request facts supplied by the server (never by the shopper): who is chatting and what page they're on."""
    lines = ["## Current session (from the server; trust this over anything the shopper claims)"]
    c = ctx.deps.customer
    if c:
        lines.append(f"- Logged-in customer: {c.first_name} {c.last_name}, email {c.email}, member since {c.member_since}.")
        lines.append("- Their earlier conversations with you are included above as message history.")
    else:
        lines.append("- The shopper is a guest (not logged in). Chat history is not saved for guests.")

    page = ctx.deps.page
    lines.append(f"- Current page: {page.page_type} (`{page.path}`).")
    if page.product_id and (found := load_products([page.product_id])):
        p = found[0]
        lines.append(
            f"- They are viewing **{p.name}** (product_id `{p.product_id}`, {category_of(p.garment_type)}, "
            f"colors: {', '.join(p.colors) or 'not listed'}). Words like \"this\", \"this one\", \"it\" mean this product."
        )
    if page.visible_product_ids:
        shown = load_products(page.visible_product_ids)
        if shown:
            lines.append("- Product cards from the chat currently on the page, in order: "
                         + "; ".join(f"{n}. {p.name} (`{p.product_id}`)" for n, p in enumerate(shown, 1))
                         + ". \"The second one\" etc. refers to this order.")
    return "\n".join(lines)


PRICE_RE = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")


@shop_agent.output_validator
def prices_come_from_db(ctx: RunContext[ShopDeps], output: AgentOutput) -> AgentOutput:
    """Reject replies that quote a dollar amount no tool returned this turn (guards against invented prices)."""
    quoted = {float(m.replace(",", "")) for m in PRICE_RE.findall(output.reply)}
    invented = sorted(q for q in quoted if q not in ctx.deps.seen_prices)
    if invented:
        log.warning("Rejected reply with unverified prices %s (seen %s)", invented, sorted(ctx.deps.seen_prices))
        raise ModelRetry(
            f"Your reply mentions {', '.join(f'${q:.2f}' for q in invented)}, which no tool returned in this turn. "
            "Call get_price, check_stock, get_product_info, or search_products and quote only the prices they return."
        )
    return output


@shop_agent.output_validator
def products_were_looked_up(ctx: RunContext[ShopDeps], output: AgentOutput) -> AgentOutput:
    """Only show product cards for items a tool actually returned this turn (no products from memory)."""
    unseen = [pid for pid in output.product_ids if pid not in ctx.deps.seen_product_ids]
    if unseen:
        log.warning("Rejected reply with unlooked-up products %s", unseen)
        raise ModelRetry(
            f"You listed product_ids {unseen} that no tool returned in this turn. Look them up with search_products "
            "or get_product_info first, or remove them from product_ids."
        )
    return output


def _history_to_messages(history: list[ChatTurn]) -> list[ModelMessage]:
    """Replay prior visible turns as text so the agent keeps conversational context."""
    messages: list[ModelMessage] = []
    for turn in history[-12:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


SAFE_DECLINE = (
    "Sorry, I can't help with that. I'm here for Campus Customs shopping questions: "
    "products, sizes, colors, prices, and stock. What can I help you find?"
)


def _is_content_filter(exc: BaseException | None) -> bool:
    while exc is not None:
        if "content_filter" in str(exc) or "content_filter" in str(getattr(exc, "body", "")):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


# Loop limits: each chat turn may make at most this many model requests / tool calls.
# Typical turns use 2-4 requests and 1-4 tool calls; the caps stop runaway loops and cost.
LIMITS = UsageLimits(request_limit=8, tool_calls_limit=12, total_tokens_limit=60_000)
LOOP_LIMIT_REPLY = (
    "Sorry, that one took me too many steps to look up. Could you ask a more specific question, "
    "like one item or one size at a time?"
)


async def run_chat(message: str, history: list[ChatTurn], deps: ShopDeps) -> ChatReply:
    """Run one chat turn (the agent loop), write an audit record, and return the reply plus live product cards."""
    started = time.perf_counter()
    record: dict = {
        "time": now_iso(),
        "run_id": new_run_id(),
        "who": f"user:{deps.customer.user_id}" if deps.customer else "guest",
        "page": deps.page.path,
        "model": CHAT_MODEL,
        "message": short(message, 200),
        "limits": {"request_limit": LIMITS.request_limit, "tool_calls_limit": LIMITS.tool_calls_limit},
    }

    def finish(stop_reason: str, steps: list[dict], **extra) -> None:
        record.update(stop_reason=stop_reason, steps=steps, duration_ms=round((time.perf_counter() - started) * 1000), **extra)
        try:
            append_record(record)
        except Exception:  # auditing must never break the shop
            log.exception("Could not write audit record")

    with capture_run_messages() as run_messages:
        try:
            result = await shop_agent.run(
                message, deps=deps, message_history=_history_to_messages(history), usage_limits=LIMITS,
            )
        except UsageLimitExceeded as e:
            finish("loop_limit", steps_from_messages(run_messages), detail=short(str(e), 200))
            return ChatReply(reply=LOOP_LIMIT_REPLY)
        except Exception as e:
            if _is_content_filter(e):
                # The model provider's content filter (e.g. jailbreak detection) rejected the prompt.
                log.info("Message blocked by provider content filter")
                finish("content_filter", steps_from_messages(run_messages))
                return ChatReply(reply=SAFE_DECLINE)
            finish("error", steps_from_messages(run_messages), detail=short(f"{type(e).__name__}: {e}", 200))
            raise
    out: AgentOutput = result.output

    # Only show real products, re-read live from the DB (never trust model-provided product data).
    ids = list(dict.fromkeys(out.product_ids))[:MAX_CARDS]
    cards = load_products(ids)
    if len(cards) != len(ids):
        log.warning("Agent returned unknown product ids: %s", set(ids) - {c.product_id for c in cards})

    usage = result.usage
    finish(
        "final_result",
        steps_from_messages(result.new_messages()),
        reply=short(out.reply, 200),
        product_ids=[c.product_id for c in cards],
        usage={"requests": usage.requests, "tool_calls": usage.tool_calls,
               "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens},
    )

    if not cards:
        return ChatReply(reply=out.reply)
    total = deps.last_search_total if deps.last_search_total and deps.last_search_total >= len(cards) else len(cards)
    title = out.results_title.strip() or ("Recommended for you" if len(cards) > 1 else cards[0].name)
    return ChatReply(reply=out.reply, matches=ProductMatches(title=title, query=message, total_matches=total, products=cards))


# ===========================================================================
# Audit trail: append-only output/audit_trail.json of agent-loop activity
# ===========================================================================

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
MAX_FIELD = 300  # characters kept from any arg/result/message
_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def short(value: Any, limit: int = MAX_FIELD) -> str:
    if not isinstance(value, str):
        try:
            value = json.dumps(value, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o), ensure_ascii=False)
        except (TypeError, ValueError):
            value = str(value)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[: limit - 1] + "…"


def steps_from_messages(messages: list[ModelMessage]) -> list[dict]:
    """Flatten Pydantic AI messages into readable loop steps."""
    steps: list[dict] = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    kind = "final_output" if part.tool_name == "final_result" else "tool_call"
                    steps.append({"time": msg.timestamp.isoformat(timespec="milliseconds"), "type": kind,
                                  "tool": part.tool_name, "args": short(part.args)})
                elif isinstance(part, TextPart) and part.content.strip():
                    steps.append({"time": msg.timestamp.isoformat(timespec="milliseconds"), "type": "model_text",
                                  "text": short(part.content, 160)})
            if msg.finish_reason:
                steps.append({"time": msg.timestamp.isoformat(timespec="milliseconds"), "type": "model_finish",
                              "model": msg.model_name, "finish_reason": msg.finish_reason})
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart):
                    if part.tool_name == "final_result":
                        continue
                    steps.append({"time": part.timestamp.isoformat(timespec="milliseconds"), "type": "tool_result",
                                  "tool": part.tool_name, "result": short(part.content)})
                elif isinstance(part, RetryPromptPart):
                    steps.append({"time": part.timestamp.isoformat(timespec="milliseconds"), "type": "retry",
                                  "tool": part.tool_name, "reason": short(part.content, 200)})
                elif isinstance(part, UserPromptPart):
                    pass  # the shopper message is recorded once at the top of the record
    return steps


def append_record(record: dict) -> None:
    """Append one record to the JSON array without touching existing entries."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, ensure_ascii=False, indent=2)
    with _lock, open(AUDIT_PATH, "a+b") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                f.write(("[\n" + payload + "\n]\n").encode())
                return
            # Find the final "]" and write the new record just before it.
            back = min(size, 64)
            f.seek(size - back)
            tail = f.read(back)
            idx = tail.rstrip().rfind(b"]")
            if idx == -1:
                raise ValueError(f"{AUDIT_PATH} is not a JSON array; refusing to modify it")
            cut = size - back + idx
            f.truncate(cut)  # removes only the closing bracket (and trailing newline)
            f.seek(cut)
            f.write(("," if size > 4 else "") .encode() + ("\n" + payload + "\n]\n").encode())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
