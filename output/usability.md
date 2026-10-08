# Usability Improvements: Campus Customs

Four improvements built in Problem 9: two on the front end and two in the agent/back end. Each one says **what was added**, **why it helps**, and **how to see it in the running app**.

| # | Area | Improvement |
|---|---|---|
| 1 | Front end | Search, filter, and sort on the Products page |
| 2 | Front end | Suggested-question chips in the chat that change with the page |
| 3 | Agent/back end | Product grounding check: the agent can only show products it actually looked up |
| 4 | Agent/back end | Chat safety: sensitive-info redaction and a rate limit |

---

## 1. Search, filter, and sort on the Products page (front end)

**What we added**
- A toolbar above the 102-item grid on `/products` with:
  - a **search box** that matches name, description, tags, and colors,
  - **category chips** (All, T-shirts, Crewnecks, Hoodies, Quarter-zips, Jackets, Long sleeve),
  - an **"In stock in my size"** dropdown (XS–XXL),
  - a **sort** menu (Featured, Price low→high, Price high→low, Name A→Z).
- A live "Showing N of 102" count and a **Clear filters** button.
- The filters are saved in the URL (e.g. `/products?q=bulldog&cat=hoodie&size=M&sort=price-asc`), so Back works and a filtered view can be shared or bookmarked.
- Product cards show a small **stock badge**. With a size filter on, it shows **"Only 2 left in XL"** when that size is low (1–5). Without one, it shows "Only a few left" or "Sold out" when every size is low or gone.

**Why it helps**
- **Shoppers** can get from 102 items to "hoodies in stock in my size, cheapest first" in two clicks, without scrolling or opening sold-out items.
- **Stock-aware filtering** prevents the most frustrating moment in apparel shopping: finding something you love and then learning your size is gone. 145 of 612 size rows are sold out.
- **Shareable URLs** let a parent text a link like "the navy crewnecks in L" to a student.
- **For the business:** faster discovery means more items seen per visit, and fewer "do you have X?" questions for staff.

**See it:** open **Products**, type "bulldog", click **Hoodies**, choose size **XL**, then sort by **Price: low to high**. Or open `/products?q=bulldog&cat=hoodie&size=XL&sort=price-asc` directly.

**Verified:** that URL shows "Showing 2 of 102 items · in stock in XL" with the two bulldog hoodies. The Sailor Bulldog card has the badge **"Only 2 left in XL"** (DB: XL = 2). The Hoodies chip is highlighted, and **Clear filters** resets everything.

**Files:** `frontend/src/pages/Products.tsx`, `frontend/src/components/ProductCard.tsx`, `frontend/src/index.css`.

---

## 2. Context-aware suggested questions in the chat (front end)

**What we added**
- A row of one-tap **suggestion chips** above the chat input. The chips change with the page you're on:
  - **Single-item page:** "Is this in stock in M?", "Other colors?", "How much is this?", "Show similar items"
  - **Products page:** "Show me hoodies", "What's under $40?", "Gifts for a Yale parent", "Bulldog gear"
  - **Logged in with chat history:** "What was I looking at last time?"
  - **Anywhere else:** a starter set.
- Tapping a chip sends it as a message right away. The chips stay out of the way while the assistant is replying.

**Why it helps**
- **Shoppers** often don't know what the assistant can do. The chips teach them by example ("Other colors?" shows it understands the current page).
- **Mobile shoppers** can ask a common question with one tap instead of typing.
- **For the business:** more shoppers actually use the assistant, and the chips steer them toward questions the agent answers best (stock, price, similar items), which leads to more product views.

**See it:** open the chat on the Home page, then on any product page, and watch the chips change. Tap **"Is this in stock in M?"**.

**Verified:** on the District Vit Hoodie Vintage Sailor Bulldog page, the chips were "Is this in stock in M?", "Does this come in other colors?", "How much is this?", and "Show me similar items". Tapping the first one got "Yes, the District Vit Hoodie Vintage Sailor Bulldog is in stock in M, with 8 left." (DB: M = 8). The page context from Problem 8 tells the agent what "this" means.

**Files:** `frontend/src/components/ChatWidget.tsx` (`suggestionsFor()`), `frontend/src/index.css`.

---

## 3. Product grounding check (agent/back end, accuracy)

**What we added**
- A second **output validator** on the Pydantic AI agent (`agent.py`, `products_were_looked_up`). Every `product_id` the agent wants to show must have come back from a tool call **in this same turn**. Each tool records the ids it returned in `ShopDeps.seen_product_ids`.
- If the agent tries to show a product it never looked up (e.g. from memory or an old message), the run is retried with a `ModelRetry` that tells it to call `search_products` or `get_product_info` first.
- On the page side, every card is still re-read from the DB (Problem 7).

**Why it helps**
- **Shoppers** only see cards that match what the assistant actually checked this turn. A stale or made-up suggestion can't appear next to an answer about a different item.
- It completes the "no invented facts" guarantee: **prices** were already checked (Problem 6), and now **which products** are shown is checked too.
- **For the business:** it protects trust. A chatbot that shows the wrong item undermines every other answer.

**See it:** server logs show `Rejected reply with unlooked-up products …` whenever the guard fires. In the app, every card in the "From your chat" panel is an item the agent looked up for that answer.

**Verified:**
- **Direct test:** calling the validator with `seen_product_ids={"basic-hoodie-big-yale"}` accepts that id but rejects `["basic-hoodie-big-yale", "yale-mom-hoodie"]` with a `ModelRetry`.
- **Live test:** when we asked the agent to "put those two back on the page" (with ids only in the old history), it called the tools again first, and both cards showed with live $68.00 prices.

**Files:** `backend/agent.py` (`products_were_looked_up`), `backend/tools.py` (`_record(..., ids=...)` in every tool), `backend/models.py` (`ShopDeps.seen_product_ids`).

---

## 4. Chat safety: sensitive-info redaction and a rate limit (agent/back end, safety)

**What we added**
- **Redaction** (the "Chat safety" section of `backend/main.py`). Before a message goes to the LLM, into the replayed history, or into `chat_messages`, the server blanks out:
  - card-like numbers (13–19 digits that pass the Luhn checksum, i.e. real card numbers),
  - SSN patterns,
  - anything that looks like a password ("my password is …").

  The shopper's bubble shows the redacted text, and the agent is told something was removed, so it can say "please don't share card numbers here."
- **Rate limit** on `POST /api/chat`: at most **12 messages per minute** per logged-in user, or per IP address for guests. Extra requests get HTTP 429 and a friendly "You're sending messages quickly, please wait a moment" in the chat.

**Why it helps**
- **Shoppers** sometimes paste a card number thinking they can check out in chat. Redaction keeps that data out of the AI provider's logs and out of our database, which protects them even when they make a mistake.
- **For the business:**
  - It avoids storing payment data, which carries a large compliance burden (PCI).
  - The rate limit caps AI spend and stops a script or bored visitor from hammering the paid model, which keeps the assistant fast for everyone else.

**See it:** type `can I pay with 4242 4242 4242 4242?` in the chat. Your bubble shows `[card number removed]`, and the assistant reminds you not to share card details. Sending 13 messages within a minute triggers the slow-down notice.

**Verified:**
- **Redaction in the browser:** the bubble changed to "can I pay with [card number removed]?". The agent replied "For your security, please don't share card numbers here. I can't take payments or check you out in chat…". A DB query found **0** rows containing the card digits; the saved row has the redacted text.
- **Redaction tests:** `my password is hunter22` → `my password is [password removed]`, and `123-45-6789` → `[SSN removed]`. A 13-digit order number that fails the Luhn check is left alone.
- **Rate limit:** 14 rapid guest messages from one IP (after 1 earlier message) gave 11 × `200` and 3 × `429`, which matches the 12-per-minute limit.

**Files:** `backend/main.py` ("Chat safety" section and `/api/chat`), `backend/models.py` (`ChatReply.message_redacted`), `frontend/src/components/ChatWidget.tsx`.

---

## Note: a speed idea we tested and dropped

We measured a baseline of **4.8 s per reply on average** (5 fixed questions) and tried lowering the model's `reasoning_effort` to make replies faster and cheaper. Through Portkey, the provider (Azure) rejects `reasoning_effort` for `gpt-5.6-terra` when function tools are used, so this setting isn't available. We switched improvement #4 to safety, which also benefits the business by capping AI spend through the rate limit.
