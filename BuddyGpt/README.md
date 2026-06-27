# BuddyGPT 🚀

BuddyGPT is a modern, AI-powered chat application built with **Flet** (Python) and powered by the **SmolLM3-3B** model from Hugging Face. It offers a fluid, efficient, and persistent chat experience similar to ChatGPT but with full control over your data and local history.

---

## ✨ Key Features

### 🌊 Real-Time Streaming
Experience a more natural interaction with **token-by-token streaming**. The assistant's response appears on the screen as it is being generated, providing immediate feedback and reducing wait times.

### 🧠 Advanced Memory & Summarization
BuddyGPT doesn't just "remember" everything; it manages context intelligently:
- **SummarizationMiddleware**: When the conversation history exceeds a certain threshold (default: 12 messages), the agent automatically summarizes the previous context.
- **Context Retention**: It keeps a sliding window of the most recent messages (default: 10) to maintain high-quality relevant answers while staying within the model's token limits.

### 💾 Persistent Conversation History
Never lose a chat. All conversations are securely stored in a local **SQLite database** using advanced reliability features. BuddyGPT utilizes the **Write-Ahead Logging (WAL)** mode to ensure superior performance and data integrity:

- **Multi-Thread Support**: Organize your thoughts across separate threads without risk of data corruption.
- **Advanced Concurrency (WAL Mode)**: This mode allows simultaneous reading and writing operations, making the app much more responsive. You will notice three files in your data folder working in perfect harmony:
    - `.db`: The main database file where all your history resides.
    - `.db-wal`: The Write-Ahead Log, which captures changes precisely as they happen for maximum safety.
    - `.db-shm`: The Shared Memory file, acting as a high-speed index to keep operations lightning fast.
This triple-file architecture is a standard of excellence in database management, providing a robust and fluid experience.

### ⚙️ User-Friendly Settings
Manage your credentials directly from the app:
- **Hugging Face Token**: Configurable through the UI and saved to a secure `.env` file.
- **LangSmith Tracing**: Optional integration for developers to trace and debug agent performance.

---

## 🛠️ Architecture

- **Backend (`src/llm_interface.py`)**: Handles the LLM logic, LangChain agents, memory middleware, and SQLite persistence via `AsyncSqliteSaver`.
- **Frontend (`src/main.py`)**: A responsive UI built with Flet, supporting dynamic header layouts, auto-scrolling, and asynchronous event handling.
- **Storage**: Organized in a dedicated `storage/` directory for data and logs.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- A Hugging Face API Token (with read access)

### Installation

#### Using `uv` (Recommended)
```bash
uv run flet run
```

#### Using `poetry`
1. Install dependencies:
   ```bash
   poetry install
   ```
2. Run the application:
   ```bash
   poetry run flet run
   ```

### First Run Configuration
1. When you first launch the app, click the **Settings ⚙️** icon in the bottom right.
2. Enter your **Hugging Face API Token**.
3. (Optional) Enter your **LangSmith API Key** if you wish to track your sessions.
4. Click **Save**. The app will initialize the model and you're ready to chat!

---

## 🐳 Docker (Experimental)
If you wish to containerize BuddyGPT, remember to:
- Include all files in the project root.
- Mount a volume for the `storage/` directory (especially `storage/data/`) to preserve your history.
- Ensure environment variables for API keys are correctly passed or configured via `.env`.

---

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information (if applicable).