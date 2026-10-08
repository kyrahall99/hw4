# Campus Customs Shop + Chatbot (HW4)

A Yale merch storefront with an AI shopping assistant:
- **Frontend:** React + Vite + TypeScript.
- **Backend:** FastAPI.
- **Agent:** a Pydantic AI agent using OpenAI models through Portkey. Its prices and stock come straight from the local SQLite database.

Shoppers can browse and filter products, create an account and log in, and chat with "Ask a Bulldog". The matching products appear on the page as cards, and the assistant gives honest per-size stock and prices.

## 1. Place the data pack (not in git)

Unzip the course data into the project root so you have:

```text
hw4/
└── data/
    ├── campus_customs.db
    └── products/        # 102 .jpg images referenced by the catalogue
```

## 2. Create `.env`

```bash
cp .env.example .env
```

Then set `PORTKEY_API_KEY` in `.env`. `CHAT_MODEL` defaults to `gpt-5.6-terra`. `SESSION_SECRET` is generated automatically if you leave it out.

## 3. Run the backend (terminal 1)

Requires Python 3.12+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

The API is at <http://127.0.0.1:8000>. A quick check is `GET /api/health`.

## 4. Run the frontend (terminal 2)

Requires Node 20+.

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/media` to the backend on port 8000.

**Test account:** `test@campuscustoms.yale.edu` / `password`, or create your own on the Create Account page.

## Project layout

```text
hw4/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── frontend/            # Vite React TypeScript app
├── backend/
│   ├── main.py          # FastAPI app — run with: uvicorn main:app --reload --port 8000
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   └── prompts/
│       └── prompt.md
└── output/
    ├── harness.md
    ├── design.md
    ├── usability.md
    ├── app_check.html
    ├── app_check_images/   # screenshots linked from app_check.html
    └── audit_trail.json
```

## Documentation

- [`output/harness.md`](output/harness.md): how the whole system works. Covers the database, auth, API contract, tools, memory, model fields, safety rules, specs, and the audit trail.
- [`output/usability.md`](output/usability.md): the four usability improvements.
- [`output/design.md`](output/design.md): the visual design and why it should help sales.
- [`output/app_check.html`](output/app_check.html): live-site test screenshots.
- [`AI_prompts.md`](AI_prompts.md): every prompt used to build this, by problem.
