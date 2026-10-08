"""Pydantic types shared by the API, the agent, and its tools."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Products (API responses and chat product cards)
# ---------------------------------------------------------------------------


class SizeStock(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    """A full catalog product with live per-size stock (what product cards render)."""
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_file_path: str
    image_url: str
    price: float
    inventory: list[SizeStock]
    total_stock: int


# ---------------------------------------------------------------------------
# Chat API
# ---------------------------------------------------------------------------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """What the shopper is looking at, sent by the website with every chat message."""
    path: str = Field(default="/", max_length=200, description="Current URL path, e.g. /products/basic-hoodie-big-yale")
    page_type: Literal["home", "products", "product_detail", "about", "login", "create_account", "other"] = "other"
    product_id: str | None = Field(default=None, max_length=100, description="Set on a single-item page.")
    visible_product_ids: list[str] = Field(default_factory=list, max_length=12, description="Cards the chat last put on the page, in order.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)  # used for guests only
    page: PageContext = Field(default_factory=PageContext)


class ProductMatches(BaseModel):
    """The structured search results the chat puts on the page (the chat -> page API contract)."""
    title: str = Field(description="Short heading for the results panel, e.g. 'Navy hoodies'.")
    query: str = Field(description="The shopper message that produced these results.")
    total_matches: int = Field(description="How many catalog items matched the agent's last search (can exceed len(products)).")
    products: list[Product] = Field(description="Cards to render, best match first, re-read live from the DB.")


class ChatReply(BaseModel):
    reply: str
    message_redacted: str | None = Field(default=None, description="The shopper's message with sensitive data removed, if anything was removed.")
    matches: ProductMatches | None = Field(default=None, description="Null when the turn has no products to show.")


class HistoryMessage(BaseModel):
    """One saved chat turn, as reloaded for a returning logged-in shopper."""
    role: Literal["user", "assistant"]
    content: str
    created_at: str
    matches: ProductMatches | None = None


class ChatHistory(BaseModel):
    messages: list[HistoryMessage]


# ---------------------------------------------------------------------------
# Agent types
# ---------------------------------------------------------------------------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]
LOW_STOCK_MAX = 5  # 1-5 units counts as "only a few left"


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_MAX else "in_stock"


class AgentOutput(BaseModel):
    """Structured output the agent must return each turn."""
    reply: str = Field(description="Your message to the shopper, in Markdown. Short and friendly.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id values (from tool results) to show as product cards on the page, best match first. Max 8. Empty if none.",
    )
    results_title: str = Field(
        default="",
        max_length=60,
        description="Short heading for the on-page results panel, e.g. 'Navy hoodies' or 'Bulldog gear under $60'. Empty if product_ids is empty.",
    )


class Customer(BaseModel):
    """The logged-in shopper, as the agent sees them (from the session cookie + users table)."""
    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date (UTC), YYYY-MM-DD.")


@dataclass
class ShopDeps:
    """Per-request context the server gives the agent (never taken from model output).

    customer is None for guests. page describes what the shopper is looking at.
    The tools also record every price they return, so the output validator can reject
    a reply that quotes a dollar amount the database never produced this turn.
    """
    customer: Customer | None = None
    page: PageContext = field(default_factory=PageContext)
    seen_prices: set[float] = field(default_factory=set)
    seen_product_ids: set[str] = field(default_factory=set)  # every product_id a tool returned this turn
    last_search_total: int | None = None  # total_matches of the most recent search_products call this turn


class SizeAvailability(BaseModel):
    size: Literal["XS", "S", "M", "L", "XL", "XXL"]
    quantity: int = Field(description="Exact units on hand right now, read from the inventory table.")
    status: StockStatus = Field(description="sold_out if 0, low_stock if 1-5, else in_stock.")


class ProductSummary(BaseModel):
    """Compact product info returned by search (enough to pick candidates, not to quote stock counts)."""
    product_id: str
    name: str
    category: str
    price: float
    colors: list[str]
    in_stock_sizes: list[str]
    sold_out_sizes: list[str]


class SearchResult(BaseModel):
    total_matches: int = Field(description="How many products matched in total (can exceed `showing`).")
    showing: int
    price_min: float | None = Field(description="Lowest price across ALL matches, not just the ones shown.")
    price_max: float | None = Field(description="Highest price across ALL matches, not just the ones shown.")
    products: list[ProductSummary]
    note: str = ""


class ProductInfo(BaseModel):
    """Everything the shopper might ask about one product, read live from catalogue + inventory."""
    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    colors: list[str]
    price: float = Field(description="Price in USD. One price for every size.")
    sizes: list[SizeAvailability] = Field(description="All six sizes, XS to XXL, with exact quantities.")
    total_stock: int
    available_sizes: list[str]
    sold_out_sizes: list[str]
    details_limited: bool = Field(description="True if the catalog only has a placeholder description for this item.")


class PriceInfo(BaseModel):
    product_id: str
    name: str
    price: float = Field(description="Price in USD. Same for every size.")
    currency: Literal["USD"] = "USD"


class StockCheck(BaseModel):
    """Answer to "do you have X in size Y?" / "how many are left?"."""
    product_id: str
    name: str
    price: float
    requested_size: str | None = Field(description="The normalized size asked about (e.g. 'M'), or null if none was asked.")
    size_exists: bool = Field(description="False if the shopper asked for a size we never sell (e.g. XXXL).")
    requested_quantity: int | None = Field(description="Exact units of the requested size, or null if no size was asked.")
    requested_status: StockStatus | None
    sizes: list[SizeAvailability] = Field(description="All six sizes so you can suggest alternatives.")
    available_sizes: list[str]
    sold_out_sizes: list[str]
    total_stock: int
    summary: str = Field(description="A plain-English, DB-generated sentence you can rely on.")


class ProductNotFound(BaseModel):
    """Returned instead of raising when a product can't be found, so the agent can recover."""
    error: str
    suggestions: list[ProductSummary] = Field(default_factory=list, description="Closest catalog matches by name.")


class ColorAlternative(BaseModel):
    product_id: str
    name: str
    colors: list[str]
    new_colors: list[str] = Field(description="Colors this item has that the original does not.")
    price: float
    in_stock_sizes: list[str]
    similar_design: bool = Field(description="True if the name shares design words (e.g. same college or sport).")


class OtherColors(BaseModel):
    product_id: str
    name: str
    colors: list[str] = Field(description="The only colors this exact item comes in.")
    note: str
    alternatives: list[ColorAlternative]
