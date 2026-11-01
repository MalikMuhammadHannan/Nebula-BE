# AI Blog Platform — Backend

A FastAPI backend for a blog platform with AI features: write blogs by hand or let an AI agent research the web and write one for you, upload documents and chat with them (RAG), like and comment on posts, manage users through a natural-language admin assistant, and buy AI tokens with Stripe.

## Tech stack

| Area | Tools |
| --- | --- |
| Web framework | FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy 2.0 (typed `Mapped` models), Alembic migrations |
| Vector search | pgvector (`vector(384)` columns, cosine distance) |
| Auth | JWT (`python-jose`), bcrypt password hashing (`passlib`) |
| Image storage | Cloudinary |
| LLM | Ollama running `qwen2.5:0.5b` via `langchain-ollama` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) via `langchain-huggingface` |
| Text splitting | LangChain `RecursiveCharacterTextSplitter` |
| Document parsing | `pypdf`, `python-docx` |
| Web research | Tavily search API, `requests` + BeautifulSoup scraping |
| Image generation | `diffusers` tiny Stable Diffusion (CPU) |
| Payments | Stripe Checkout + webhooks |
| Dependency management | Poetry |

## Project structure

```
BE/
├── alembic/                  # Database migrations
│   ├── env.py                # Loads app models so autogenerate sees them
│   └── versions/             # One file per schema change
├── alembic.ini
├── pyproject.toml            # Poetry dependencies
└── app/
    ├── main.py               # FastAPI app, CORS, router registration
    ├── config.py             # Reads settings from .env
    ├── core/
    │   ├── security.py       # hash_password / verify_password (bcrypt)
    │   └── jwt.py            # create_access_token, get_current_user, require_admin
    ├── database/
    │   ├── base.py           # SQLAlchemy DeclarativeBase
    │   └── session.py        # Engine, session factory, get_db dependency
    ├── models/               # SQLAlchemy tables
    │   ├── user.py           # User (role, is_active, token_balance)
    │   ├── blogs.py          # Blog (slug, image, embedding)
    │   ├── comments.py       # Comment
    │   ├── like.py           # Like (unique per blog+user)
    │   ├── document.py       # Uploaded document
    │   ├── document_chunk.py # Text chunk + embedding
    │   ├── chat_turn.py      # Q&A history per document
    │   └── purchase.py       # Stripe token purchase
    ├── schema/               # Pydantic request/response models
    ├── api/                  # Route handlers (one router per feature)
    ├── ai/                   # LLM, embeddings, chunking, agents, tools, token accounting
    └── services/             # Cloudinary, Stripe, Tavily, scraper, document extractor, image generator
```

---

## How the app was built, step by step

The steps below follow the order the features were added (see `git log`).

### Step 1 — Project setup (`first commit`)

- Created the project with Poetry (`pyproject.toml`, Python 3.12+).
- Added FastAPI and Uvicorn.
- Added `app/config.py`, which loads every setting from a `.env` file with `python-dotenv`.
- Added `.gitignore` for virtualenvs, `.env`, caches and editor folders.

### Step 2 — Database, User model and migrations (`feat : create user model and run migrations`)

- **`app/database/base.py`** — a `Base` class that every model inherits from.
- **`app/database/session.py`** — creates the SQLAlchemy engine from `DATABASE_URL` and a `get_db()` dependency that opens a session per request and always closes it.
- **`app/models/user.py`** — the `users` table: `full_name`, unique `email`, `password_hash`, `role` (`user` / `editor` / `admin`), `is_active`, `is_verified`, `created_at`, `updated_at`.
- Initialised Alembic. `alembic/env.py` imports `Base` and all models so `alembic revision --autogenerate` detects changes.
- First migration: **`b614378dcd87_initial_tables`**.

### Step 3 — Authentication (`create blog crud`)

- **`app/core/security.py`** — bcrypt password hashing and verification with `passlib`.
- **`app/core/jwt.py`**
  - `create_access_token()` signs a JWT containing the user id (`sub`), email and role, with an expiry of `ACCESS_TOKEN_EXPIRE_MINUTES`.
  - `get_current_user()` is a FastAPI dependency that reads the `Bearer` token, decodes it and loads the user from the database. Any protected route uses `Depends(get_current_user)`.
- **`app/api/auth.py`**
  - `POST /auth/register` — rejects duplicate emails, hashes the password, saves the user.
  - `POST /auth/login` — checks the password and that the account is active, then returns the access token and the user.

### Step 4 — Blog CRUD (`create blog crud`)

- **`app/models/blogs.py`** — the `blogs` table: `title`, unique `slug`, `description`, `content`, `image_url`, `image_public_id`, `is_published`, `author_id` → `users.id`, timestamps. `User.blogs` / `Blog.author` relationship.
- **`app/schema/blogs.py`** — `BlogCreate`, `BlogUpdate` (all fields optional), `BlogResponse`.
- **`app/api/blogs.py`**
  - `POST /blogs/` — create a blog; the slug is generated from the title with `python-slugify`.
  - `GET /blogs/` — the logged-in user's own blogs.
  - `PATCH /blogs/{id}` — partial update (`model_dump(exclude_unset=True)`); only the author may edit.
  - `DELETE /blogs/{id}` — only the author may delete.
- Added CORS middleware in `main.py` so the Vite frontend (`http://localhost:5173`) can call the API.

### Step 5 — Image upload with Cloudinary (`create blog crud`, `add crud for image upload`)

- **`app/services/cloudinary.py`** (started alongside blog CRUD)
  - `upload_image()` uploads a file (or a remote URL) into the `blogs` folder and returns its secure URL and public id.
  - `delete_upload_image()` turns a Cloudinary URL back into a public id (strips `/upload/`, the version segment and the extension) and deletes the image.
- **`app/api/upload.py`** — `POST /upload/image` takes a multipart file and returns `image_url` and `public_id`.
- Blog update deletes the old image when the image URL changes, and blog delete removes its image.

### Step 6 — Public blog API (`feat : create api for public blog`)

- `GET /blogs/public` — every blog, no login required.
- `GET /blogs/public/{id}` — one blog, no login required.

### Step 7 — Document upload and chunking (`start doc chunking`, `upload document`)

This is the first half of a RAG (retrieval-augmented generation) pipeline.

- Enabled the **pgvector** extension (`CREATE EXTENSION IF NOT EXISTS vector`) in migration **`0f43f8bb7c1d`**, which also creates:
  - **`documents`** — `filename`, `file_type`, `status` (`pending` / `processing` / `processed` / `failed`), `owner_id`.
  - **`document_chunks`** — `chunk_text`, `chunk_index`, `embedding vector(384)`.
- **`app/services/document_extractor.py`** — validates the extension (`pdf`, `docx`, `txt`) and extracts plain text with `pypdf` / `python-docx` / UTF-8 decoding.
- **`app/ai/chunking.py`** — splits text into ~500-character chunks with 50 characters of overlap, preferring paragraph, line and sentence boundaries.
- **`app/ai/embeddings.py`** — a singleton that lazily loads `all-MiniLM-L6-v2` once and exposes `embed_texts()` (for indexing) and `embed_query()` (for searching).
- **`app/api/document.py`**
  - `POST /document/upload` — saves a `Document` with status `processing`, extracts → chunks → embeds the text, stores each chunk, then marks it `processed` (or `failed` on any error). The document id is returned as `session_id`.
  - `GET /document/all` — the user's documents.
  - `DELETE /document/{session_id}` — deletes the document with its chunks and chat history.
- Migration **`e0e93b456ca7`** adds an `embedding vector(384)` column to `blogs`. Blog create/update now embeds `title + description + content`, and re-embeds when any of those change.
- Added `app/test-embedding.py` and `app/test-image.py` as quick scripts to check the embedding model and the image generator (`app/services/image_generator.py`, tiny Stable Diffusion on CPU).

### Step 8 — Likes and comments (`like comment`)

- **`app/models/comments.py`** — `comments` table (`content`, `blog_id`, `user_id`), cascade-deleted with the blog or user.
- **`app/models/like.py`** — `likes` table with a unique constraint `(blog_id, user_id)` so a user can like a blog only once.
- Relationships added on `User` and `Blog` (`comments`, `likes`) with `cascade="all, delete-orphan"`.
- Migrations **`28995f14e594`** and **`57e8377c6700`**.
- **`app/api/comment.py`**
  - `POST /blogs/{blog_id}/comments` — add a comment.
  - `GET /blogs/{blog_id}/comments` — list comments, newest first.
  - `DELETE /comments/{comment_id}` — only the comment's author may delete.
- **`app/api/likes.py`**
  - `POST /blogs/{blog_id}/like` — like; the unique constraint turns a second like into `400 Already liked`.
  - `DELETE /blogs/{blog_id}/like` — unlike.
  - Both return the new `total_likes`.

### Step 9 — Chat with a document (`feat : chat history`, `fix : chat history`)

The second half of the RAG pipeline.

- **`app/models/chat_turn.py`** + migration **`3f905f250cd6`** — `document_chat_turns` stores every question, whether an answer was found, and the answer's title, description and content.
- **`app/ai/llm.py`** — `LLMService` wraps a local Ollama model (`qwen2.5:0.5b`, temperature 0.2, max 400 tokens).
- `POST /document/query` with `{ session_id, query }`:
  1. Checks the document belongs to the user.
  2. Loads the last 5 Q&A turns as conversation history.
  3. Embeds the question and fetches the 5 closest chunks by **cosine distance** in pgvector.
  4. If the closest chunk is further than `0.75`, records "not found" and returns `[]` — the model is never asked to guess.
  5. Otherwise sends history + chunks + question to the LLM with a prompt that forbids outside knowledge.
  6. Builds a title (first 8 words) and description (first sentence) from the answer, saves the turn and returns it in the same shape as a blog.
- `GET /document/{session_id}/history` — the full Q&A history in order.

### Step 10 — AI blog generation with tool calling (`feat : tool calling`)

An agent researches a topic on the web, then writes a blog post.

- **`app/services/web_search.py`** — Tavily search, returns title, URL and snippet for 5 results.
- **`app/services/web_scraper.py`** — fetches a page, removes `script`/`style`/`nav`/`footer`/`header`, returns up to 4000 characters of text and up to 5 absolute image URLs.
- **`app/ai/blog_tools.py`** — wraps both as LangChain `@tool`s: `search_web_tool` and `scrape_url_tool`.
- **`app/ai/llm.py`** — a second model instance, `tool_model`, without `repeat_penalty`, because the penalty breaks tool calling on the small Qwen model.
- **`app/ai/blog_agent.py`** — `generate_blog_from_query()`:
  1. Binds the tools to the model and runs a loop (max 8 steps).
  2. Executes every tool call the model makes and feeds results back as `ToolMessage`s.
  3. If the model stops without scraping anything, nudges it to scrape the best search result.
  4. If a scrape comes back empty, falls back to the other URLs from the last search automatically (the small model tends to retry the same dead link).
  5. Once a page has been scraped, asks the model to write `TITLE:` / `DESCRIPTION:` / `CONTENT:`.
  6. `_parse_blog_text()` strips stray HTML tags, splits on those labels, and fills any missing field from the content.
- **`app/api/ai_blog.py`** — `POST /ai-blogs/generate` with `{ query }` runs the agent, uploads the first scraped image that Cloudinary accepts, embeds the text and saves the blog under the current user.

### Step 11 — Admin user management with an AI assistant (`feat : admin user inactive`, `feat : admin user status update`)

- **`require_admin`** in `app/core/jwt.py` — dependency that returns `403` unless `role == "admin"`.
- Login now refuses inactive users (`403 User is not active`).
- **`app/ai/user_tools.py`** — `activate_user_tool` and `deactivate_user_tool`; both search users by partial, case-insensitive name or email. The tool the model picks tells us the intended action.
- **`app/ai/user_agent.py`** — `find_users_from_query()` sends the admin's sentence (e.g. *"deactivate Ali"*) to the model and returns `{ action, matches }`.
- **`app/api/users.py`** (admin only):
  - `GET /users/` — all non-admin users.
  - `POST /users/assistant` — returns the action, the matching users and a confirmation message such as *"Found Ali (ali@x.com). Deactivate this user?"*.
  - `POST /users/{user_id}/deactivate` and `POST /users/{user_id}/activate` — require `{ "confirm": true }`, so the AI only *suggests*; a human confirms the change.

### Step 12 — AI token billing with Stripe (`feat : stripe token`, `fix : stripe issue`)

- Migration **`5682e071cc67`** adds `token_balance` to `users`; migration **`6a2d72f2659b`** adds the **`purchases`** table (`package`, `tokens`, `amount` in cents, `status`, unique `idempotency_key`, Stripe session and payment intent ids, `completed_at`).
- **`app/ai/token_usage.py`** — reads `total_tokens` from a LangChain response's `usage_metadata`.
- AI endpoints (`/ai-blogs/generate`, `/document/query`) return `402` when the balance is 0 and subtract the tokens actually used after each call.
- **`app/ai/token_packages.py`** — three packages mapped to Stripe price ids:

  | Package | Tokens | Price (USD) |
  | --- | --- | --- |
  | `starter` | 50,000 | 5 |
  | `standard` | 150,000 | 9 |
  | `pro` | 500,000 | 20 |

- **`app/services/stripe_service.py`** — creates a Checkout Session (with `purchase_id` in metadata, success/cancel URLs on `FRONTEND_URL`) and verifies webhook signatures.
- **`app/api/billing.py`**
  - `GET /billing/packages` — list packages.
  - `GET /billing/tokens` — current balance.
  - `POST /billing/checkout-session` — creates a pending `Purchase`, then a Stripe session. An optional `Idempotency-Key` header makes retries return the same session instead of charging twice. If Stripe fails, the pending purchase is deleted.
  - `POST /billing/webhook` — on `checkout.session.completed` with `payment_status == "paid"`, credits the tokens and marks the purchase `completed`. Already-completed purchases are skipped, so a repeated webhook can't credit twice.

---

## Database schema

```
users ─┬─< blogs ─┬─< comments >─┐
       │          └─< likes >────┤
       ├──────────────────────────┘ (comments.user_id, likes.user_id)
       ├─< documents ─┬─< document_chunks
       │              └─< document_chat_turns
       └─< purchases
```

Migration order: `b614378dcd87` initial → `0f43f8bb7c1d` documents + chunks → `e0e93b456ca7` blog embedding → `28995f14e594` comments + likes → `57e8377c6700` relationships → `3f905f250cd6` chat turns → `5682e071cc67` token balance → `6a2d72f2659b` purchases.

## API reference

🔒 = needs `Authorization: Bearer <token>`, 👑 = admin only.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Get an access token |
| GET | `/blogs/public` | All blogs |
| GET | `/blogs/public/{id}` | One blog |
| POST | `/blogs/` 🔒 | Create a blog |
| GET | `/blogs/` 🔒 | My blogs |
| PATCH | `/blogs/{id}` 🔒 | Update my blog |
| DELETE | `/blogs/{id}` 🔒 | Delete my blog |
| POST | `/upload/image` | Upload an image to Cloudinary |
| POST | `/blogs/{blog_id}/comments` 🔒 | Add a comment |
| GET | `/blogs/{blog_id}/comments` | List comments |
| DELETE | `/comments/{comment_id}` 🔒 | Delete my comment |
| POST | `/blogs/{blog_id}/like` 🔒 | Like a blog |
| DELETE | `/blogs/{blog_id}/like` 🔒 | Unlike a blog |
| POST | `/ai-blogs/generate` 🔒 | Research the web and write a blog (uses tokens) |
| POST | `/document/upload` 🔒 | Upload PDF / DOCX / TXT and index it |
| GET | `/document/all` 🔒 | My documents |
| POST | `/document/query` 🔒 | Ask a question about a document (uses tokens) |
| GET | `/document/{session_id}/history` 🔒 | Q&A history |
| DELETE | `/document/{session_id}` 🔒 | Delete a document |
| GET | `/users/` 👑 | List non-admin users |
| POST | `/users/assistant` 👑 | Natural-language activate/deactivate lookup |
| POST | `/users/{user_id}/activate` 👑 | Activate (requires `confirm: true`) |
| POST | `/users/{user_id}/deactivate` 👑 | Deactivate (requires `confirm: true`) |
| GET | `/billing/packages` | Token packages |
| GET | `/billing/tokens` 🔒 | My token balance |
| POST | `/billing/checkout-session` 🔒 | Start a Stripe Checkout |
| POST | `/billing/webhook` | Stripe webhook |

Interactive docs are at `http://localhost:8000/docs` once the server is running.

## Running locally

### Prerequisites

- Python 3.12+ and [Poetry](https://python-poetry.org/)
- PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension installed
- [Ollama](https://ollama.com/) with the model pulled: `ollama pull qwen2.5:0.5b`
- Accounts/keys for Cloudinary, Tavily and Stripe
- The [Stripe CLI](https://stripe.com/docs/stripe-cli) to forward webhooks locally

### 1. Install dependencies

```bash
poetry install
```

### 2. Create `.env`

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ai_blog_platform
SECRET_KEY=<random-long-string>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

TAVILY_API_KEY=

STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
FRONTEND_URL=http://localhost:5173
```

### 3. Create the database and run migrations

```bash
createdb ai_blog_platform
poetry run alembic upgrade head
```

Alembic reads its connection string from `sqlalchemy.url` in `alembic.ini`; make sure it matches your database.

### 4. Start the server

```bash
poetry run uvicorn app.main:app --reload
```

The first start downloads the embedding model and the tiny Stable Diffusion model from Hugging Face, so it takes a while.

### 5. Forward Stripe webhooks (for billing)

```bash
stripe listen --forward-to localhost:8000/billing/webhook
```

Put the `whsec_...` secret it prints into `STRIPE_WEBHOOK_SECRET`.

### 6. Make an admin

New users get `role = "user"`. Promote one in SQL:

```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```

## Known issues / next steps

- `GET /blogs/{id}` returns the query object instead of `.first()`, and it is shadowed for the public use case by `/blogs/public/{id}`.
- `POST /upload/image` doesn't require login.
- `alembic.ini` contains a hard-coded database password; it should read `DATABASE_URL` from the environment instead.
- `blogs.slug` is unique but `POST /blogs/` uses the bare slugified title, so two blogs with the same title fail on insert (AI blogs already add a random suffix).
- `app/services/image_generator.py` loads Stable Diffusion at import time even though its use in `/document/query` is commented out, which slows startup.
- `is_verified` exists on `User` but there is no email verification flow yet.
- `app/services/auth_service.py` is empty.
- No automated tests yet.
