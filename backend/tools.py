"""Read-only catalog access and the tools the shop agent can call.

Every price and stock number the agent says must come from these functions,
which read the SQLite database live on each call.
"""

import json
import re
import sqlite3
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    ColorAlternative, Customer, OtherColors, PriceInfo, Product, ProductInfo, ProductNotFound, ProductSummary, SearchResult, ShopDeps, SizeAvailability,
    SizeStock, StockCheck, stock_status,
)

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "campus_customs.db"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_RANK_SQL = "CASE size " + " ".join(f"WHEN '{s}' THEN {i}" for i, s in enumerate(SIZE_ORDER)) + " END"
STUB_MARKER = "Vision blocked"

# garment_type has 22 messy values; map them to a few shopper-friendly categories.
CATEGORIES = ["t-shirt", "long-sleeve shirt", "crewneck", "hoodie", "full-zip hoodie", "quarter-zip", "jacket"]


def category_of(garment_type: str) -> str:
    g = garment_type.lower()
    if "quarter-zip" in g:
        return "quarter-zip"
    if "full-zip hood" in g:
        return "full-zip hoodie"
    if "jacket" in g:
        return "jacket"
    if "hood" in g:
        return "hoodie"
    if "long-sleeve" in g:
        return "long-sleeve shirt"
    if "t-shirt" in g:
        return "t-shirt"
    return "crewneck"  # crewneck / raglan / mockneck sweatshirts


# Shopper words -> words that appear in the catalog.
SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "shirt": "t-shirt", "shirts": "t-shirt",
    "hoodies": "hoodie", "hoody": "hoodie", "hooded": "hoodie", "sweatshirt": "crewneck", "sweatshirts": "crewneck",
    "crew": "crewneck", "crews": "crewneck", "crewnecks": "crewneck", "sweater": "fleece",
    "quarterzip": "quarter-zip", "1/4": "quarter-zip", "zip": "zip", "jackets": "jacket", "fleeces": "fleece",
    "grey": "gray", "navy": "navy", "dan": "bulldog", "handsome": "bulldog", "bulldogs": "bulldog", "dog": "bulldog",
    "ua": "under armour", "armour": "under armour", "armor": "under armour", "mom": "mom", "dad": "dad",
}
STOPWORDS = {"a", "an", "the", "any", "do", "you", "have", "got", "u", "with", "on", "it", "for", "me", "some", "show",
             "in", "of", "and", "or", "your", "what", "whats", "is", "are", "i", "want", "looking", "need", "yale", "merch",
             "something", "anything", "word", "please", "can", "get", "find", "item", "items", "stuff"}

# ---------------------------------------------------------------------------
# Database access (read-only)
# ---------------------------------------------------------------------------


def connect_ro() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def load_products(product_ids: list[str] | None = None) -> list[Product]:
    """Load products with live per-size stock. Keeps catalog order, or the order of product_ids if given."""
    con = connect_ro()
    try:
        where, params = "", ()
        if product_ids is not None:
            if not product_ids:
                return []
            where = f"WHERE product_id IN ({','.join('?' * len(product_ids))})"
            params = tuple(product_ids)
        rows = con.execute(f"SELECT * FROM catalogue {where} ORDER BY rowid", params).fetchall()
        stock: dict[str, list[SizeStock]] = {}
        for r in con.execute(f"SELECT product_id, size, quantity FROM inventory {where} ORDER BY product_id, {SIZE_RANK_SQL}", params):
            stock.setdefault(r["product_id"], []).append(SizeStock(size=r["size"], quantity=r["quantity"]))
    finally:
        con.close()

    products = []
    for r in rows:
        inv = stock.get(r["product_id"], [])
        products.append(Product(
            product_id=r["product_id"], name=r["name"], garment_type=r["garment_type"], description=r["description"],
            colors=json.loads(r["colors"]), search_tags=json.loads(r["search_tags"]),
            image_file_path=r["image_file_path"], image_url="/media/" + r["image_file_path"],
            price=r["price"], inventory=inv, total_stock=sum(s.quantity for s in inv),
        ))
    if product_ids is not None:
        order = {pid: i for i, pid in enumerate(product_ids)}
        products.sort(key=lambda p: order[p.product_id])
    return products


def _normalize_size(size: str) -> str | None:
    s = size.strip().upper().replace("-", "").replace(" ", "")
    aliases = {"EXTRASMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M", "LARGE": "L", "EXTRALARGE": "XL",
               "XLARGE": "XL", "2XL": "XXL", "XXLARGE": "XXL", "2XLARGE": "XXL"}
    s = aliases.get(s, s)
    return s if s in SIZE_ORDER else None


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9/'-]+", text.lower().replace("’", "'"))
    out = []
    for w in words:
        w = w.strip("'-")
        if not w or w in STOPWORDS:
            continue
        out.append(SYNONYMS.get(w, w.rstrip("s") if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w))
    return out


def _haystack(p: Product) -> dict[str, str]:
    name = p.name.lower().replace("1 4 zip", "quarter-zip 1/4 zip").replace("t shirt", "t-shirt").replace("ua ", "under armour ")
    return {
        "name": name,
        "type": f"{p.garment_type.lower()} {category_of(p.garment_type)}",
        "tags": " ".join(p.search_tags).lower(),
        "desc": p.description.lower(),
        "colors": " ".join(p.colors).lower(),
    }


def search_catalog(query: str = "", category: str | None = None, color: str | None = None,
                   max_price: float | None = None, size: str | None = None, limit: int = 8) -> SearchResult:
    products = load_products()
    notes = []
    if category:
        cat = category.lower().strip()
        cat = {"tee": "t-shirt", "t-shirts": "t-shirt", "hoodies": "hoodie", "crewnecks": "crewneck", "sweatshirt": "crewneck",
               "quarter zip": "quarter-zip", "1/4 zip": "quarter-zip", "jackets": "jacket", "fleece": "jacket"}.get(cat, cat)
        if cat in CATEGORIES:
            products = [p for p in products if category_of(p.garment_type) == cat
                        or (cat == "hoodie" and category_of(p.garment_type) == "full-zip hoodie")]
        else:
            notes.append(f"Unknown category '{category}'. Valid categories: {', '.join(CATEGORIES)}.")
    if color:
        c = color.lower().strip().replace("grey", "gray")
        products = [p for p in products if any(c in col.lower() for col in p.colors)]
    if max_price is not None:
        products = [p for p in products if p.price <= max_price]
    norm_size = None
    if size:
        norm_size = _normalize_size(size)
        if norm_size is None:
            notes.append(f"Size '{size}' does not exist. Sizes sold: {', '.join(SIZE_ORDER)}.")
        else:
            products = [p for p in products if any(s.size == norm_size and s.quantity > 0 for s in p.inventory)]

    terms = _tokens(query)
    if terms:
        scored = []
        for p in products:
            h = _haystack(p)
            score = 0
            for t in terms:
                score += 4 * (t in h["name"]) + 3 * (t in h["type"]) + 2 * (t in h["tags"]) + (t in h["desc"]) + (t in h["colors"])
            if score:
                scored.append((score, p))
        scored.sort(key=lambda x: -x[0])
        products = [p for _, p in scored]

    limit = max(1, min(limit, 12))
    shown = products[:limit]
    return SearchResult(
        total_matches=len(products),
        showing=len(shown),
        price_min=min((p.price for p in products), default=None),
        price_max=max((p.price for p in products), default=None),
        products=[_summary(p) for p in shown],
        note=" ".join(notes),
    )


def _summary(p: Product) -> ProductSummary:
    return ProductSummary(
        product_id=p.product_id, name=p.name, category=category_of(p.garment_type), price=p.price, colors=p.colors,
        in_stock_sizes=[s.size for s in p.inventory if s.quantity > 0],
        sold_out_sizes=[s.size for s in p.inventory if s.quantity == 0],
    )


def resolve_product(product: str) -> Product | ProductNotFound:
    """Find one product by exact product_id, or by name if the id isn't exact."""
    key = product.strip()
    found = load_products([key])
    if not found:
        slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        found = load_products([slug]) if slug else []
    if not found:
        exact = [p for p in load_products() if p.name.lower() == key.lower()]
        found = exact[:1]
    if found:
        return found[0]
    candidates = search_catalog(key, limit=5).products
    return ProductNotFound(
        error=f"No product matches '{product}' exactly. If one of the suggestions is what the shopper meant, call again with its product_id; otherwise use search_products.",
        suggestions=candidates,
    )


def _sizes(p: Product) -> list[SizeAvailability]:
    return [SizeAvailability(size=s.size, quantity=s.quantity, status=stock_status(s.quantity)) for s in p.inventory]


def product_info(p: Product) -> ProductInfo:
    return ProductInfo(
        product_id=p.product_id, name=p.name, category=category_of(p.garment_type), garment_type=p.garment_type,
        description=p.description, colors=p.colors, price=p.price, sizes=_sizes(p), total_stock=p.total_stock,
        available_sizes=[s.size for s in p.inventory if s.quantity > 0],
        sold_out_sizes=[s.size for s in p.inventory if s.quantity == 0],
        details_limited=STUB_MARKER in p.description,
    )


def stock_check(p: Product, size: str | None) -> StockCheck:
    sizes = _sizes(p)
    available = [s.size for s in sizes if s.quantity > 0]
    sold_out = [s.size for s in sizes if s.quantity == 0]
    req, exists, qty, status = None, True, None, None
    if size:
        req = _normalize_size(size)
        if req is None:
            exists, req = False, size.strip()
        else:
            row = next(s for s in sizes if s.size == req)
            qty, status = row.quantity, row.status

    if not exists:
        summary = f"We don't make the {p.name} in size {req}; sizes are {', '.join(SIZE_ORDER)}."
    elif req and qty == 0:
        summary = f"The {p.name} is SOLD OUT in {req}."
    elif req:
        summary = f"The {p.name} has {qty} left in {req}" + (" (low stock)." if status == "low_stock" else ".")
    else:
        summary = f"The {p.name} has {p.total_stock} units in stock across all sizes."
    if req and (qty == 0 or not exists):
        summary += f" Available sizes: {', '.join(available)}." if available else " It is sold out in every size."
    elif not req and sold_out:
        summary += f" Sold out in: {', '.join(sold_out)}."
    return StockCheck(
        product_id=p.product_id, name=p.name, price=p.price, requested_size=req, size_exists=exists,
        requested_quantity=qty, requested_status=status, sizes=sizes, available_sizes=available,
        sold_out_sizes=sold_out, total_stock=p.total_stock, summary=summary,
    )

# ---------------------------------------------------------------------------
# Agent tools
#
# Every tool reads the database on each call and records the prices it returns
# in ctx.deps.seen_prices so the agent's reply can be checked against them.
# ---------------------------------------------------------------------------


def _record(ctx: RunContext[ShopDeps], *prices: float | None, ids: tuple[str, ...] | list[str] = ()) -> None:
    ctx.deps.seen_prices.update(p for p in prices if p is not None)
    ctx.deps.seen_product_ids.update(ids)


def search_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    limit: int = 8,
) -> SearchResult:
    """Search the Campus Customs catalog. Use this to find products for any "do you have / show me" question.

    Args:
        query: Keywords from the shopper, e.g. "bulldog", "Berkeley college", "hockey", "Champion". Can be empty when filtering.
        category: Optional filter. One of: t-shirt, long-sleeve shirt, crewneck, hoodie, full-zip hoodie, quarter-zip, jacket.
        color: Optional color filter, e.g. "navy", "gray", "white".
        max_price: Optional maximum price in dollars.
        size: Optional size the shopper needs (XS, S, M, L, XL, XXL); only items in stock in that size are returned.
        limit: How many products to return (1-12, default 8).

    Returns total_matches (may be more than shown), price range across ALL matches, and which sizes are in stock.
    For exact quantities, call check_stock.
    """
    result = search_catalog(query, category, color, max_price, size, limit)
    _record(ctx, max_price, result.price_min, result.price_max, *(p.price for p in result.products),
            ids=[p.product_id for p in result.products])
    ctx.deps.last_search_total = result.total_matches
    return result


def get_product_info(ctx: RunContext[ShopDeps], product: str) -> ProductInfo | ProductNotFound:
    """Get the full live record for one product: description, colors, price, and exact stock for every size.

    Use for "tell me about…", "what does it look like", "what colors", or before recommending a specific item.

    Args:
        product: The product_id (preferred, from a search result or the page being viewed) or the exact product name.
    """
    p = resolve_product(product)
    if isinstance(p, ProductNotFound):
        return p
    _record(ctx, p.price, ids=[p.product_id])
    return product_info(p)


def get_price(ctx: RunContext[ShopDeps], product: str) -> PriceInfo | ProductNotFound:
    """Look up the current price of one product. Call this for every "how much is…" question.

    Args:
        product: The product_id (preferred) or the exact product name.
    """
    p = resolve_product(product)
    if isinstance(p, ProductNotFound):
        return p
    _record(ctx, p.price, ids=[p.product_id])
    return PriceInfo(product_id=p.product_id, name=p.name, price=p.price)


def check_stock(ctx: RunContext[ShopDeps], product: str, size: str | None = None) -> StockCheck | ProductNotFound:
    """Check live stock for one product, optionally for one size. Call this for every availability question
    ("is it in stock", "do you have it in M", "how many are left").

    Args:
        product: The product_id (preferred) or the exact product name.
        size: The size the shopper asked about, in any form ("medium", "M", "2XL", "extra large"). Omit to get every size.

    Returns exact quantities per size, a status (in_stock / low_stock / sold_out), and a reliable `summary` sentence.
    """
    p = resolve_product(product)
    if isinstance(p, ProductNotFound):
        return p
    _record(ctx, p.price, ids=[p.product_id])
    return stock_check(p, size)


def find_other_colors(ctx: RunContext[ShopDeps], product: str) -> OtherColors | ProductNotFound:
    """Answer "do you have this in other colors?". Each catalog item comes in ONE colorway, so this finds
    the closest sibling items (same category, similar design or name) in different colors.

    Args:
        product: The product_id (preferred; use the page's product when the shopper says "this") or exact name.
    """
    p = resolve_product(product)
    if isinstance(p, ProductNotFound):
        return p
    _record(ctx, p.price, ids=[p.product_id])
    base_cat = category_of(p.garment_type)
    base_colors = {c.lower() for c in p.colors}
    base_words = set(_tokens(p.name)) - {"t-shirt", "hoodie", "crewneck", "quarter-zip", "jacket"}
    scored = []
    for q in load_products():
        if q.product_id == p.product_id or category_of(q.garment_type) != base_cat:
            continue
        new_colors = [c for c in q.colors if c.lower() not in base_colors]
        if not new_colors:
            continue
        overlap = len(base_words & set(_tokens(q.name)))
        scored.append((overlap, q, new_colors))
    scored.sort(key=lambda x: -x[0])
    similar = scored[:6]
    _record(ctx, *(q.price for _, q, _ in similar), ids=[p.product_id, *(q.product_id for _, q, _ in similar)])
    return OtherColors(
        product_id=p.product_id, name=p.name, colors=p.colors,
        note="This exact item is only made in the colors listed. These similar items in the same category come in other colors.",
        alternatives=[ColorAlternative(product_id=q.product_id, name=q.name, colors=q.colors, new_colors=nc, price=q.price,
                                       in_stock_sizes=[s.size for s in q.inventory if s.quantity > 0],
                                       similar_design=ov > 0) for ov, q, nc in similar],
    )


def get_customer_profile(ctx: RunContext[ShopDeps]) -> Customer | str:
    """Who is chatting: the logged-in customer's name, email, and member-since date. Returns a message for guests."""
    return ctx.deps.customer or "The shopper is a guest (not logged in), so no profile is available."


TOOLS = [search_products, get_product_info, get_price, check_stock, find_other_colors, get_customer_profile]
