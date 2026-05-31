# AI_PR Review Agent

> An autonomous multi-agent system that automatically reviews GitHub Pull Requests using LangGraph orchestration, semantic memory, and specialized AI agents - delivering structured code reviews directly as PR comments.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-green)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-teal)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Database-green)](https://www.mongodb.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-red)](https://qdrant.tech/)

---

## What It Does

When a Pull Request is opened or updated on GitHub, this system:

1. **Fetches the PR diff** from GitHub and searches for similar past reviews
2. **Analyzes the changes** — what files changed, what was added/removed
3. **Detects bugs** — syntax errors, logical issues, security vulnerabilities, edge cases
4. **Reviews code style** — PEP 8, type hints, docstrings, naming conventions
5. **Synthesizes a final verdict** — APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION
6. **Posts a concise summary** directly as a PR comment on GitHub
7. **Stores the full review** in MongoDB and Qdrant for future context

---

## Architecture

```mermaid
graph TD
    A[👤 GitHub PR Opened/Synchronized] --> B[🌐 FastAPI Webhook Endpoint]
    B --> C[🔄 Background Task Queue]
    C --> D[🧠 LangGraph Orchestrator]

    D --> E[🔍 Agent 1: Diff Analyzer]
    E --> E1[GitHub API — fetch diff & PR info]
    E --> E2[Qdrant — search similar past reviews]

    E --> F[🐛 Agent 2: Bug Detector]
    F --> F1[Analyze for bugs, security issues, edge cases]

    F --> G[🎨 Agent 3: Style Reviewer]
    G --> G1[Check PEP 8, type hints, docstrings, naming]

    G --> H[⚖️ Agent 4: Judge]
    H --> H1[Synthesize all reports]
    H --> H2[Generate verdict + summary]
    H --> H3[Post comment to GitHub PR]
    H --> H4[Save to MongoDB + Qdrant]

    subgraph Memory & Storage
        I[🔷 Qdrant — Semantic search over past reviews]
        J[🍃 MongoDB — PR history, metadata, acceptance rate]
        K[📊 LangSmith — Full agent traces & observability]
        L[💾 SQLite — LangGraph checkpointing]
    end

    H4 --> I
    H4 --> J
    D -.->|Traces| K
    D -.->|State| L
```

---

## Key Features

- **Multi-agent pipeline** — 4 specialized agents, each with a distinct role
- **Semantic memory** — Qdrant stores past reviews; similar PRs surface relevant context automatically
- **Hybrid search** — Dense embeddings (Gemini) + Cohere reranking for best retrieval quality
- **Background processing** — FastAPI responds to GitHub in <2s; review runs asynchronously
- **Full observability** — Every agent run traced in LangSmith with latency breakdowns
- **Checkpointing** — SQLite-backed LangGraph state; failed reviews can resume mid-pipeline
- **Structured storage** — MongoDB with Beanie ODM stores full review history and acceptance rate analytics

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | Groq (llama-3.3-70b-versatile) |
| Embeddings | Google Gemini (gemini-embedding-001) |
| Reranking | Cohere rerank-english-v3.0 |
| Vector Store | Qdrant |
| Document Store | MongoDB + Beanie ODM |
| Checkpointing | SQLite |
| API | FastAPI |
| GitHub Integration | PyGithub |
| Observability | LangSmith |
| Containerization | Docker Compose |

---

## Project Structure

```
PR_ReviewAgent/
├── agents/
│   ├── diff_analyzer.py      # Agent 1 — PR diff analysis + past context
│   ├── bug_detector.py       # Agent 2 — Bug, security & edge case detection
│   ├── style_reviewer.py     # Agent 3 — PEP 8, type hints, docstrings
│   └── judge.py              # Agent 4 — Synthesize, verdict, post comment
├── graph/
│   └── workflow.py           # LangGraph state machine + SQLite checkpointing
│   └── background.py         # Async background review task
├── memory/
│   ├── mongo_store.py        # MongoDB CRUD operations
│   └── qdrant_store.py       # Qdrant vector store + hybrid search
├── schema/
│   ├── state.py              # PRReviewState — Pydantic LangGraph state
│   └── review.py             # PRReview — Beanie document model
├── tools/
│   └── github_tools.py       # GitHub API — fetch diff, post comments
├── main.py                   # FastAPI endpoints
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- ngrok (for local webhook testing)

### 1. Clone the repository

```bash
git clone https://github.com/VinayParmar555/PR_ReviewAgent.git
cd PR_ReviewAgent
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Fill in your API keys in `.env`:

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
COHERE_API_KEY=your_cohere_key
GITHUB_TOKEN=your_github_pat
MONGO_URI=mongodb://admin:admin@localhost:27017
QDRANT_URL=http://localhost:6333
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=pr-review-agent
```

### 3. Start with Docker

```bash
docker compose up --build
```

FastAPI server starts at `http://localhost:8000`

### 4. Set up GitHub Webhook

```bash
# Expose local server
ngrok http 8000
```

GitHub -> Repository -> Settings -> Webhooks -> Add webhook:
- **Payload URL:** `https://your-ngrok-url/webhook/github`
- **Content type:** `application/json`
- **Events:** Pull requests

### 5. Raise a PR and watch the magic

Open a Pull Request on your repository — the agent will automatically post a review comment within ~15 seconds.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhook/github` | GitHub webhook receiver |
| `GET` | `/review/{owner}/{repo}/{pr}` | Manually trigger a review |
| `GET` | `/stats/{owner}/{repo}` | Review history & acceptance rate |

### Manual trigger example

```bash
curl http://localhost:8000/review/VinayParmar555/PR_ReviewAgent/3
```

---

## Observability

All agent runs are traced in LangSmith:

```
LangGraph
  ├── diff_analyzer    ~4.9s   (GitHub API + Gemini embedding)
  ├── bug_detector     ~2.1s   (LLM analysis)
  ├── style_reviewer   ~2.1s   (LLM analysis)
  └── judge            ~4.6s   (2x LLM + MongoDB + Qdrant)

Average P50 latency: ~15s
```

---

## Future Improvements

- **Parallel execution** — Run bug_detector and style_reviewer simultaneously via LangGraph parallel edges (~40% latency reduction)
- **Inline comments** — Post line-specific comments instead of general PR comments
- **Webhook signature verification** — HMAC-SHA256 validation for production security
- **Multi-language support** — Extend style reviewer to JavaScript, Go, Java
- **Dashboard** — React frontend for review history and analytics

---

## License

MIT License — see [LICENSE](LICENSE) for details.
