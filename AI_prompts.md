# AI Prompts Log — Homework 4: Campus Customs Shop + Chatbot

This file logs the prompts I typed to my AI coding assistant (Claude Code) throughout the assignment, one section per problem.

---

## Problem 1: Vibe coder prompts

**Prompt 1**

```text
We are doing my Homework 4: Campus Customs Shop + Chatbot for my AI class. Please create a folder called hw4 and store the rest of this work there.
```

**Prompt 2**

```text
I'm going to give you the scenario and data for this homework assignment so that you can have it as context and as the general guiding principles for this assignment. The scenario is that Campus Customs needs a real customer website with a helpful chatbot. You will build a React + Vite TypeScript frontend and a Python Fast API backend whose brain is a Pydantic AI agent. Shoppers should be able to:

* browse products
* create an account
* chat about merch
* see matching items appear on the page
* get honest answers about price and stock from a local database

 You are given campus_customs.db with tables for the product catalog, inventory by size, and users with hashed passwords. Product image file paths are in the catalog table. Research yalebulldogblue.com to learn the style of the Campus Customs page and information for your agent prompt. Use your portkey_API_key, or whatever API key you have, for your agent's AI calls. If using OpenAI through portkey, use any models in the 5.6 or 6 series. You may want a smarter model for harder agent steps. Work one problem at a time with your vibe coder.  In the end, you will push your product project to a public GitHub repo and submit the repo URL on Canvas. The last problem shows the file tree. Do not commit the database or product images. There is a data zip file with all of the data, and I will upload that to the chat.
```

**Prompt 3**

```text
Download node.js
```

**Prompt 4**

```text
Download and setup
```

**Prompt 5**

```text
Please us the PORTKEY_API_KEY in the .env file in the root.
```

**Prompt 6**

```text
@"/Users/kyrahall/Downloads/data (1).zip"
Unzip
```

**Prompt 7**

```text
Create AI_prompts.md and keep it updated as we work. This file is the log of what I typed throughout the whole assignment. Put one section for each problem. Each section must include the problem number and title, and at least one prompt that I typed out. I will let you know when we're moving on to the next problem and what to call it. This was problem 1: vibe coder prompts.
```

---

## Problem 2: Analyze the database

**Prompt 1**

```text
Okay, we're moving on to Problem 2: Analyze the database.
```

**Prompt 2**

```text
Problem 2 says look at the database data/campus_customs.db and understand the fields of each table. At a minimum, you should understand catalog, inventory, and users. Start the file output/harness.md. Write down each table and its fields, and one short line on why each field matters for the shop or the chatbot. We will keep growing this harness file in later problems.
```

---

## Problem 3: Build the Campus Customs website

**Prompt 1**

```text
Okay, we're moving on to Problem 3: Build the Campus Customs website. Problem 3 says Scaffold a React + Vite + TypeScript frontend for Campus Customs. Put a nav bar at the top that links to the main pages, including:

* Home
* Products
* About Us
* Login
* Create Account

Pull Campus Customs style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice. Do not copy the original site text. On the Products page, show product images from the catalog, using the image paths in the database, with basic product info like name, price, and a short description. Make each product open a single item page with a large image on one side and full product text on the other, like description, price, sizes, and in stock. When you have them, clicking a card on products should take the shopper there.

Add a chat interface in the bottom right of the site. A floating chat panel is fine. It does not need to talk to an agent yet. A stub that will call your backend later is enough for this problem. You will need a small API soon to read the database. It is fine to start a simple, fast API app in backend/main.py, just to serve products and images, then grow it into the agent backend in problem 5.
```

---

## Problem 4: Create account and login

**Prompt 1**

```text
Okay, we're moving on to Problem 4: Create account and login. Problem 4 says Build a normal create-account/login flow. 

* Create account: first name, last name, email, password, and confirm password.
* Log in: email and password

New accounts go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them.
The seed database already has a test user you can use while building:

* Email: test@campuscustoms.yale.edu
* Password: password


Confirm you can log in as that user and that a brand-new account you create also works. Update output/harness.md with how authorization works, in other words, what you store for a user and how passwords are protected.
```

---

## Problem 5: Pydantic AI agent backend

**Prompt 1**

```text
Okay, great, we're moving on to Problem 5: Pydantic AI agent backend. Problem 5 says Build the shop chatbot as a Pydantic AI agent behind fast API, plugged into your frontend chat widget. Put the API app in backend/main.py. That is the file you run with Uvicorn. Keep the agent as these four files next to it:

* backend/prompts/prompt.md (system prompt - grow this same file later)
* backend/agent.py (agent entry/wiring)
* backend/tools.py (tools the agent can call)
* backend/models.py (Pydantic/Pydantic AI structured types)

In main.py, expose a chat route so a message from the website returns a reply from the agent, and whatever else you need for products/auth. We will need the AI model API key for the agent. 
Put Campus Customs voice and safety basics into prompts/prompt.md. We will expand tools and safety later.
Start or update types in models.py for chat replies/product cards as needed. In output/harness.md, note how the frontend talks to FastAPI and how the agent is loaded (prompt file + model). Make sure the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000
```

---

## Problem 6: Tools: product info and stock

**Prompt 1**

```text
Okay, great! Let's move on to Problem 6: Tools: product info and stock. 

Give the agent tools that look up real information from campus_customs.db, including product description, price, how many are in stock (by size when the customer asks). The agent must use the database. It should not invent prices or quantities. If a size is out of stock, say so clearly. 
Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why.
```

---

## Problem 7: Chat search that updates the page

**Prompt 1** (interrupted and re-sent)

```text
Okay, fantastic. Let's move on to Problem 7: Chat search that updates the page. 

Now I want to add a cool, dynamic feature to the site. When a customer asks about a type of item, the agent should search the catalogue, and the website should dynamically show those matching items as product cards, including image, name, price, and short info. This is an API contract: the agent returns structured product matches, and then the frontend renders them on the website.
```

**Prompt 2**

```text
Okay, fantastic. Let's move on to Problem 7: Chat search that updates the page. 

Now I want to add a cool, dynamic feature to the site. When a customer asks about a type of item, the agent should search the catalogue, and the website should dynamically show those matching items as product cards, including image, name, price, and short info. This is an API contract: the agent returns structured product matches, and then the frontend renders them on the website. 
After the dynamic product cards are loaded by the new feature, make sure the same single-item page behavior you built in problem 3 still works. Each product card, including the ones the chat just put on the page, should still open the detail view with large image and full info when clicked. Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.
```

---

## Problem 8: Customer memory

**Prompt 1**

```text
Okay, great. Let's move on to Problem 8: Customer memory.

When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name and email) -- put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call.

Also, pass enough page context that if someone is on a product page and asks, "do you have this in other colors?" the agent knows which item they mean. Hint: you can put code into the agent context. 

Guests can still chat, but history only needs to persist for logged-in users. Document the following in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed.
```

---

## Problem 9: Usability improvements

**Prompt 1**

```text
Fantastic. Let's move on to Problem 9: Usability improvements. 

Now that the core shop works, let's improve it. Choose and implement the following:

* 2 front-end usability improvements
* 2 agent/back-end usability improvements

Front-end improvements are things that make the site look better and make it easier to use. Agent/back-end improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper.

Write output/usability.md before or as you build. For each of the improvements, say: 

* What you added
* Why it helps a Campus Customs shopper or the business.
```

**Prompt 2**

```text
Once you finish problem 8,  move on to Problem 9: Usability improvements.
Now that the core shop works, let's improve it. Choose and implement the following:

* 2 front-end usability improvements
* 2 agent/back-end usability improvements

Front-end improvements are things that make the site look better and make it easier to use. Agent/back-end improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper.
Write output/usability.md before or as you build. For each of the improvements, say:

* What you added
* Why it helps a Campus Customs shopper or the business.

Then make sure all improvements actually show up in the running app. Homework graders will read the write-up and look for these features.
```

**Prompt 3**

```text
Problem 8 and 9 got interrupted. Are we caught up?
```

---

## Problem 10: Style the website

**Prompt 1**

```text
Okay, great, let's move on to Problem 10: Style the website. 
Add creative design so the site feels like a real campus custom storefront, including fonts, color hierarchy, motion, product presentation, and chat feel. We will get more points for imaginative and innovative design. 

Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short.
```

---

## Problem 11: Site testing (app check)

**Prompt 1**

```text
Okay, let’s move on to Problem 11: Site testing (app check). 
Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for:

1. Chat checking the inventory level of an item (honest stock/price from the DB)
2. The dynamic search-result cards appearing after a category question (e.g., hoodies)
3. One of the usability features you added in Problem 9


Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png).
```

---

## Problem 12: Audit trail, safety, finish harness

**Prompt 1**

```text
Great, let’s move on to Problem 12: Audit trail, safety, finish harness.
Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop season). Do not wipe it between runs. Also, think of some safety rules to give the agent and put them in prompts/prompt.md. Finish output/harness.md so it is clear how the system works.

* Model fields in models.py and why you chose them
* Tools and abilities
* Safety rules
* Specs (loop limits, result caps, models, how to run front + back)
```

---

## Problem 13: Push to GitHub and submit the URL

**Prompt 1**

```text
Problem 13: Push to GitHub and submit the URL
Put your code in a folder named hw4 and push it to a public GitHub repository. On Canvas, submit the repo URL (the link graders can open and clone). Do not put your real .env, campus_customs.db, or product image in the GitHub repo. Use .gitignore. Include .env.example with placeholders only.
And check to make sure this is the file layout:
[two screenshots: expected file layout tree, and local-only data pack]
```
