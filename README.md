# Enterprise RAG + AI Agent Platform

A modern, full-stack **Retrieval-Augmented Generation (RAG)** application powered by an autonomous **AI Agent**, **LangChain**, **FastAPI**, **ChromaDB**, and **React 18** with **Vite** and **Tailwind CSS**.

---

## 🌟 Key Features

- **Document Ingestion Engine**:
  - Drag-and-drop file upload supporting **PDF**, **DOCX**, and **TXT** files (up to 25MB).
  - High-performance text extraction preserving document structure and page numbers.
  - Semantic text chunking using `RecursiveCharacterTextSplitter`.
  - ChromaDB persistent vector storage with local indexing.
  - Delete and inspect document footprints, file sizes, and indexed chunks.

- **Intelligent AI Knowledge Agent**:
  - Autonomous ReAct Agent built with **LangChain** and **LangGraph**.
  - Document Search Tool (`search_documents`) to semantically retrieve relevant context.
  - Precise page and snippet source citations displayed on every assistant response.
  - Strict grounding: The agent answers based on uploaded knowledge and explicitly states when information is unavailable.
  - ChatGPT-style responsive chat UI with copy-to-clipboard, auto-resizing input, and quick prompt chips.

- **Modern SaaS Dashboard**:
  - Live metric cards: Total uploaded documents, processed documents, chunks indexed, and questions asked.
  - Real-time backend connectivity and AI model configuration status indicators.
  - Recent activity feed tracking uploads, deletions, and chat sessions.
  - Responsive layout with collapsible sidebar, top navigation, and clean Tailwind design (Indigo & Slate theme).

---

## 🏗️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Tailwind CSS, React Router DOM, Axios, Lucide React Icons |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, LangChain, LangGraph, Pydantic v2 |
| **AI & Embeddings** | OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`) |
| **Vector DB** | ChromaDB (Persistent Vector Store) |
| **Document Parsers** | PyPDF, python-docx, docx2txt |

---

## 📁 Project Structure

```text
RAG AI Agent/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   ├── routes/
│   │   │   ├── documents.py        # Upload, list, delete document APIs
│   │   │   ├── chat.py             # Chat endpoint with AI Agent
│   │   │   ├── health.py           # System and Chroma health check
│   │   │   └── stats.py            # Dashboard metrics API
│   │   ├── services/
│   │   │   ├── document_loader.py  # PDF, DOCX, TXT loaders & chunking
│   │   │   ├── vector_store.py     # ChromaDB vector store service
│   │   │   ├── rag_agent.py        # LangChain AI Agent with search tool
│   │   │   └── storage.py          # Metadata & activity persistence
│   │   ├── config.py               # Pydantic settings & environment configuration
│   │   └── main.py                 # FastAPI application and CORS setup
│   ├── data/                       # ChromaDB vectors and uploaded files
│   ├── requirements.txt            # Python dependencies
│   ├── run.py                      # Backend launcher
│   ├── test_endpoints.py           # Automated unit tests for backend APIs
│   └── .env.example                # Backend environment template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx         # Navigation sidebar with branding
│   │   │   ├── Navbar.jsx          # Top bar with backend status pill
│   │   │   ├── StatCard.jsx        # Reusable metric card
│   │   │   ├── ChatMessage.jsx     # User & AI message bubbles with source accordion
│   │   │   ├── ChatInput.jsx       # Auto-resizing input with Enter to send
│   │   │   ├── FileUpload.jsx      # Drag-and-drop upload with progress bar
│   │   │   └── DocumentCard.jsx    # Document card with metadata & delete
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # Analytics dashboard & system overview
│   │   │   ├── Documents.jsx       # Document management & search
│   │   │   ├── Chat.jsx            # Interactive AI Agent chat interface
│   │   │   └── Settings.jsx        # Configuration & system status
│   │   ├── services/
│   │   │   └── api.js              # Centralized Axios API client
│   │   ├── App.jsx                 # Routing and shell layout
│   │   ├── main.jsx                # React root mount
│   │   └── index.css               # Tailwind CSS and custom scrollbars
│   ├── package.json                # Frontend dependencies
│   ├── vite.config.js              # Vite bundler configuration
│   └── .env.example                # Frontend environment template
├── sample_documents/               # Ready-to-use PDF, DOCX, and TXT files
│   ├── company_policy.txt
│   ├── technical_specs.txt
│   ├── sample_guide.pdf
│   └── project_brief.docx
├── run_backend.bat                 # One-click Windows launcher for backend
├── run_frontend.bat                # One-click Windows launcher for frontend
└── README.md                       # Complete documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: Version 3.10, 3.11, 3.12, or 3.13.
- **Node.js**: Version 18+ (tested on Node v20/v24 with npm).
- **OpenAI API Key**: An active OpenAI API key for embeddings and agent responses.

---

### 2. Backend Setup

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. (Optional if already created) Set up a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   Open `backend/.env` and insert your OpenAI API key:
   ```ini
   OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   CHROMA_PERSIST_DIRECTORY=./data/chroma
   UPLOAD_DIRECTORY=./data/uploads
   HOST=0.0.0.0
   PORT=8000
   ```

5. Run automated backend tests:
   ```bash
   python test_endpoints.py
   ```

6. Start the FastAPI backend server:
   ```bash
   python run.py
   ```
   *The backend will be live at `http://localhost:8000` with Swagger documentation available at `http://localhost:8000/docs`.*

---

### 3. Frontend Setup

1. Open a new terminal and navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Ensure `.env` is configured:
   ```ini
   VITE_API_BASE_URL=http://localhost:8000
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```
   *The React dashboard will be live at `http://localhost:5173`.*

---

## ⚡ One-Click Windows Launchers

For convenience on Windows, double-click:
- `run_backend.bat` — Launches the FastAPI backend server on port 8000.
- `run_frontend.bat` — Launches the Vite React frontend on port 5173.

---

## 🧪 Testing the Application

1. **Open the Dashboard**: Navigate to `http://localhost:5173` in your browser.
2. **Upload Knowledge Files**:
   - Go to the **Documents** page (`/documents`).
   - Drag and drop or browse to select one of the provided sample files from `sample_documents/`:
     - `sample_documents/company_policy.txt`
     - `sample_documents/technical_specs.txt`
     - `sample_documents/sample_guide.pdf`
     - `sample_documents/project_brief.docx`
   - Watch the progress bar index the text chunks into ChromaDB.
3. **Chat with the AI Agent**:
   - Go to the **AI Agent Chat** page (`/chat`).
   - Try asking questions directly about the uploaded documents, such as:
     - *"What is the company policy regarding remote work and core hours?"*
     - *"How much is the home office equipment allowance and what are the reimbursement terms?"*
     - *"What vector embedding model and chunk size does the technical spec use?"*
   - Notice the AI Agent executes the `search_documents` tool, answers accurately, and provides expandable document sources with page numbers and snippet citations.
   - Ask an out-of-scope question (e.g., *"What is the capital of Mars?"*) and observe that the agent adheres to strict grounding, confirming the uploaded documents do not contain that information.
4. **Inspect Metrics**:
   - Return to the **Dashboard** (`/`) to see your real-time updated metrics and recent activity log.
5. **Check Settings**:
   - Visit the **Settings** page (`/settings`) to verify model configurations, embedding parameters, and database health.

---

## 📡 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check, vector DB status, and OpenAI configuration |
| `GET` | `/api/stats` | Dashboard statistics, total chunks, and recent activities |
| `GET` | `/api/documents` | List all uploaded and indexed documents |
| `POST` | `/api/documents/upload` | Upload and chunk PDF, DOCX, or TXT file into ChromaDB |
| `DELETE` | `/api/documents/{id}` | Remove document and its vectors from ChromaDB |
| `POST` | `/api/chat` | Send question to AI Agent with message history and receive cited response |

---

## 🛡️ License & Credits
Built with ❤️ using FastAPI, LangChain, ChromaDB, and React.

