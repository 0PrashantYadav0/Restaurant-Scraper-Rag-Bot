# SETUP INSTRUCTIONS

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/) [![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)

A full-stack **Retrieval-Augmented Generation (RAG)** chatbot that scrapes live restaurant data, builds a searchable knowledge base, and serves a modern web UI. Ideal for demoing how to ground large-language-model responses in up-to-date, real-world data.

---


## Install `uv` (CLI helper)

- **macOS:**  

  ```bash
  brew install uv
  ```

- **Linux:**

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **Windows (PowerShell):**

  ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- **Or via pip:**

  ```bash
  pip install uv
  ```

## 🚀 Quickstart

1. **Clone & enter**

   ```bash
   git clone https://github.com/0PrashantYadav0/Restaurant-Scraper-Rag-Bot.git
   cd Restaurant-Scraper-Rag-Bot
   ```

2. **Install deps**

   ```bash
   uv add -r requirements.txt
   cd frontend && npm install
   npm run build
   cd ..
   ```

3. **Collect & process data**

   ```bash
   uv run main.py --scrape
   uv run main.py --build-kb
   ```

4. **Run servers**
   - **Backend API**:

     ```bash
     uv run main.py --backend
     ```

     (defaults to http://localhost:8000)  
   - **Frontend UI**:

     ```bash
     cd frontend
     npm run dev
     ```

     (defaults to http://localhost:5173)

5. **Run Frontend and Backend in Production Mode** (optional)

   ```bash
   cd frontend
   npm run build
   cd ..
   uv run main.py --backend
   ```

   (defaults to http://localhost:8000)

6. **Access the app**
    - Open your browser and navigate to [http://localhost:5173](http://localhost:5173) for the frontend UI.
    - The backend API is available at [http://localhost:8000](http://localhost:8000).

### Note

You can also run the backend and frontend in production mode by building the frontend app and serving it with FastAPI. This is useful for deployment or when you want to run everything in a single terminal.

---

## 🗂️ Project Structure

```tree
├── ARCHITECTURE.md           # System design & data flow
├── config.py                 # ← your settings
├── data/
│   ├── raw/                  # Unprocessed scrape outputs
│   └── processed/            # Cleaned JSON/CSV for RAG
├── frontend/                 # React/Vue web app
│   ├── public/
│   └── src/
│       └── …                  
├── logs/                     # Application logs
├── main.py                   # Entry point
├── models/
│   └── index/                # Serialized vector DB files
├── requirements.txt          # Python dependencies
├── SETUP.md                  # Detailed setup guide
├── src/
│   ├── api/                  # FastAPI route definitions
│   ├── chatbot/              # RAG pipeline & LLM integration
│   ├── knowledge_base/       # Embedding, vector store helpers
│   ├── scraper/              # Web-scraping scripts
│   └── utils/                # Shared helpers
└── pyproject.toml            # Project metadata
```

---

### Data Workflow

| Task                        | Command                                 |
|-----------------------------|-----------------------------------------|
| Scrape new restaurant data  | `uv run main.py --scrape`               |
| Build or update KB index    | `uv run main.py --build-kb`             |
| Run backend server          | `uv run main.py --backend`              |
| Run frontend server         | `cd frontend && npm run dev`             |
| Run frontend in production  | `uv run main.py --backend`               |

---

## 🐞 Troubleshooting

| Issue                                       | Solution                                                                                       |
|---------------------------------------------|------------------------------------------------------------------------------------------------|
| **`uvicorn: command not found`**            | Run as module: `python -m uvicorn main:app --reload`                                           |
| **`pip` refers to old Python**              | Use versioned pip: `python3.10 -m pip install --upgrade pip` then `python3.10 -m pip install …` |
| **npm command not found / PATH issues**     | Ensure Node.js 18+ is installed and restart your shell                                         |
| **Frontend build errors**                   | Delete `frontend/node_modules/` then `npm install`                                             |
| **Permission errors on install**            | Use a virtualenv or add `--user` to pip, or run shell as Administrator/root                     |
| **CORS/API not reachable**                  | Enable CORS in FastAPI (`from fastapi.middleware.cors import CORSMiddleware`), check ports     |

---

## 🤝 Contributing

1. Fork & clone  
2. Create feature branch: `git checkout -b feat/your-feature`  
3. Commit & push: `git commit -m "feat: add X"` → `git push origin feat/your-feature`  
4. Open a PR—be sure to run tests & linting first!

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.