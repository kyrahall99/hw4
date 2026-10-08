# Design: Campus Customs Storefront

**Goal:** make the site feel like walking into a campus shop on Broadway, with pennants, felt letters, and a Bulldog behind the counter, while making each step toward a purchase shorter.

## Fonts
- **Fraunces** (a variable collegiate serif) for headings, prices, and the brand. **Inter** for body and UI text. Both are self-hosted via `@fontsource`, so there are no third-party font requests.
- **Why:** a serif display face feels like varsity lettering and old-campus signage, so the shop looks like Yale rather than a template. Inter keeps sizes, stock counts, and forms easy to read.

## Color hierarchy
- **Navy `#00356b`** is the brand and every primary action (buttons, active nav, the chat).
- **Gold `#c99a2e`** is used *only* for highlights: the hero's "Bulldog", the "Shop all merch" CTA, the price underline, the low-stock badges, the active-tab tick, and the ticker.
- **Cream/paper `#fffdf8`** for backgrounds instead of stark white.
- **Why:** with one accent color, the eye goes to what matters: price, scarcity, and the next action. Cream feels warm and retail rather than clinical.

## Motion (all disabled under `prefers-reduced-motion`)
- **Hero:** a YALE **pennant** that gently waves, a stitched **felt "Y" patch** that bobs, and a rotating "EST. NEW HAVEN" stamp. The headline lines rise in one after another.
- A gold **ticker** scrolls campus phrases ("12 residential colleges · Harvard–Yale ready…") and pauses on hover.
- **Product cards** fade up in a stagger, lift on hover, and the garment tilts slightly toward the shopper.
- The **chat** pops open with a spring, messages slide in, and a three-dot "Checking the shelves…" indicator shows while it works. The launcher has a soft gold pulse.
- **Why:** small, purposeful motion signals a live shop and rewards exploring without slowing anyone down. The pulse draws attention to the assistant, which is the fastest path to the right size.

## Product presentation
- **Cards:**
  - a soft "studio" backdrop,
  - a garment-type tag (HOODIE, TEE),
  - a **size strip that appears on hover** (navy = in stock, gold = low, struck through = sold out),
  - a large tabular price, and "View →".
- **Detail page:**
  - breadcrumbs,
  - a **sticky photo with hover-to-zoom** (magnifies toward the cursor to inspect prints),
  - **color swatches**,
  - **tap-to-select size buttons** with a live note ("Size XL: 2 in stock, so grab it soon"), and sold-out sizes hatched,
  - an **"Ask about this item"** button that opens the chat already asking about the selected size,
  - trust perks (licensed, live stock, pickup at 57 Broadway).
- **Home:** collection **pennant cards** (Hoodies, Crewnecks, Quarter-zips, Game Day Tees) jump straight into a filtered Products view.
- **Why:** shoppers see stock *before* clicking, see detail *before* deciding, and get honest urgency ("only 2 left") at the moment of choice. Fewer dead ends means more add-to-bag intent.

## Chat feel
- Rebranded **"Ask a Bulldog"**:
  - a navy/gold launcher with the **CC crest**,
  - a header with an online dot and "Chatting as Handsome · history saved",
  - a crest avatar beside each assistant bubble,
  - a dotted "notebook paper" background,
  - rounded bubbles with tails,
  - gold "🛍️ N items shown on the page" tags,
  - a gold Send pill.
- Any button on the site can open it with a question ready (`openChat()`): the hero's "Ask a Bulldog", Home's "Try it", and the detail page's "Ask about this item".
- **Why:** a named, on-brand assistant feels like a helpful store employee, not a generic widget. Opening it already pointed at the right question removes the blank-box problem.

## Brand details
- An SVG **CC shield crest** in the nav, chat, and launcher.
- An announcement bar with gold ✦ separators.
- A frosted sticky header that gains a shadow on scroll.
- A varsity-striped footer edge.
- Rounded pill buttons with a spring hover.
- Gold focus rings for keyboard users.

**Files:** `frontend/src/index.css` (rewritten design system), `components/Crest.tsx`, `NavBar.tsx`, `ProductCard.tsx`, `ChatWidget.tsx`, `pages/Home.tsx`, `pages/ProductDetail.tsx`, `chatEvents.ts`.
