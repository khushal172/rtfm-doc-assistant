# RTFM Agent 🧠🤖

A modern, high-performance **Documentation Assistant** that provides context-aware answers from your technical documents. Built with **FastAPI**, **Next.js**, and **Upstash**, featuring strict data isolation, semantic caching, and long-term user memory.
![RTFM Agent Banner](https://raw.githubusercontent.com/khushal172/rtfm-agent/main/banner.png)
## 🚀 Key Features

- **GitHub Intelligence**: Paste any public GitHub repository URL to locally index its documentation and source code with zero rate limits. Support for optional Personal Access Tokens (PAT).
- **Multi-Tenancy & Brain Isolation**: Cryptographically scoped contexts ensure strict data isolation. Every vector is tagged and filtered by `user_id` and `brain_id` at the database layer.
- **Hybrid Semantic Search**: Uses Gemini `gemini-embedding-2-preview` (1536-dim) for high-precision retrieval.
- **Isolated Semantic Caching**: Instant answers for identical queries, scoped specifically to each brain.
- **Long-Term Memory**: The agent extracts facts about you during conversations to provide personalized context.
- **Glassmorphic UI**: A premium, responsive dark-mode interface built with Tailwind CSS v4 and React.
- **Markdown Support**: Rich text rendering with professional citations and source tracking.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js 16 (TypeScript), Tailwind CSS v4
- **AI/LLM**: Google Gemini 2.5 Flash
- **Embeddings**: Google Gemini Embedding v2
- **Vector DB**: Upstash Vector (Serverless)
- **Memory/Cache**: Upstash Redis (Serverless)
- **Auth**: Clerk

## 📦 Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- API Keys for: Google Gemini, Upstash (Vector & Redis), and Clerk.

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/khushal172/rtfm-agent.git
cd rtfm-agent

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure .env (Copy .env.sample)
cp .env.sample .env
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🌐 Deployment Guide

### Backend (Render)
1. Create a new **Web Service** on Render.
2. Connect your GitHub repository.
3. Use the following settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add all environment variables from `.env` to the Render Dashboard.

### Frontend (Vercel)
1. Create a new project on Vercel.
2. Import the `frontend` directory.
3. Add the `NEXT_PUBLIC_API_URL` environment variable pointing to your Render backend.
4. Deploy!

## 🔐 Security & Privacy
RTFM Agent implements strict **Multi-Tenancy** at the database layer. Every document segment (vector) and cache entry is tagged with a composite metadata key including Clerk `user_id` and `brain_id`. Data retrieval processes perform strict metadata filtering before returning any context, ensuring that cross-tenant and cross-brain data leakage is mathematically impossible. The backend strictly verifies JWTs via JWKS on every request.

---
Built with ❤️ by Khushal
