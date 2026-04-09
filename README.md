# Research Assistant Agent (COM6104 Project)

A conversational AI research assistant with agentic capabilities, tool integration, and short-term memory for academic research support.

## 🌟 Features

- **Agentic AI Architecture**: Implements a two-step reasoning process with optional tool calling
- **Short-term Memory**: Tracks conversation history and extracts key entities for context awareness
- **Web-based Chat Interface**: Interactive UI with message bubbles, code block formatting, and copy functionality
- **Academic Paper Search**: Integrates with Semantic Scholar API to find relevant research papers
- **Experiment Status Tracking**: Checks local experiment log files for research progress
- **MCP Compliance**: Tools follow Model Context Protocol standards for structured interactions
- **Markdown Support**: Rich text responses with code blocks, lists, and formatting

## 🛠️ Architecture Overview

### Core Components

1. **Agent Layer** (`agent.py`)
   - Main research agent with memory and tool orchestration
   - Two-step LLM reasoning: initial response → tool call (if needed) → final response
   - Tool parsing and execution logic

2. **Memory System** (`memory.py`)
   - Short-term conversation history (configurable length)
   - Entity extraction for key research topics and references
   - Context injection into prompts

3. **LLM Client** (`llm_client.py`)
   - Ollama integration with Qwen3:8b model
   - Error handling and response formatting

4. **Web Interface** (`ui/`)
   - FastAPI backend with WebSocket-like chat functionality
   - HTML/CSS frontend with Tailwind CSS styling
   - Real-time message display with code block support

### Tools (MCP Compliant)

1. **`lookup_paper`** (`tools/paper_tool.py`)
   - Queries Semantic Scholar API for academic papers
   - Returns structured results with title, authors, abstract, year, and URL
   - Includes rate limiting protection and retry logic
   - Automatically triggered by academic keywords

2. **`check_experiment_status`** (`tools/experiment_tool.py`)
   - Checks for experiment log files in `~/experiments/` directory
   - Converts paper titles to safe filenames for log lookup
   - Returns status, file path, last entry, and line count
   - Handles file reading errors gracefully

## 📋 Installation & Setup

### Prerequisites

- Python 3.8+
- Ollama (https://ollama.com)
- Internet connection (for Semantic Scholar API)

### Installation Steps

1. **Install Ollama and required model**:
   ```bash
   # Install Ollama from https://ollama.com
   ollama pull qwen3:8b
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages include:
   - fastapi
   - uvicorn
   - ollama
   - requests
   - markdown
   - pymdown-extensions

3. **Create experiment directory** (optional but recommended):
   ```bash
   mkdir -p ~/experiments
   # Create sample log file for testing
   echo "[2026-02-27] Initial experiment completed." > ~/experiments/diffusion_model.log
   ```

## ▶️ Running the Application

### Method 1: Using Batch Script (Windows)
```bash
# Run the startup script
start.bat
```
This will:
- Start the FastAPI server on port 8000
- Automatically open your browser to http://localhost:8000

### Method 2: Manual Startup
```bash
# Start the server manually
uvicorn ui.main:app --reload --port 8000

# Open your browser to: http://localhost:8000
```

## 💬 Usage Examples

### Academic Paper Search
The system automatically detects academic queries containing keywords like:
- "paper", "research", "study", "academic"
- "文献", "论文", "published", "author"
- "journal", "conference", "cite", "引用"

**Example queries:**
- "Find recent papers about diffusion models"
- "What are the latest studies on transformer architectures?"
- "查找关于强化学习的最新论文"

### Experiment Status Checking
Ask about specific experiments to check their log files:
- "Check the status of my diffusion model experiment"
- "What's the latest update on my GAN research?"

### General Conversation
For non-academic queries, the agent provides general assistance without tool calls.

## 🔧 Configuration

### Model Configuration
Edit `llm_client.py` to change the LLM model:
```python
MODEL_NAME = "qwen3:8b"  # Change to your preferred model
```

### Memory Settings
Adjust memory parameters in `memory.py`:
```python
def __init__(self, max_history: int = 3):  # Change history length
```

### Academic Keywords
Modify trigger keywords in `ui/main.py`:
```python
ACADEMIC_KEYWORDS = [  # Add or remove keywords
    "paper", "research", "study", "academic", "文献", "论文", 
    "published", "author", "journal", "conference", "cite", "引用",
    "survey", "review", "find papers", "最新研究", "相关工作"
]
```

## 📊 MCP Compliance

Both tools inherit from the `MCPTool` base class and provide:
- Structured JSON input/output
- Tool metadata via `get_spec()` method
- No side effects (pure functions)
- Error handling with structured responses

Tested with MCP Inspector v1.2 compatibility.

## 🚀 Development Notes

- The web interface supports Markdown formatting including code blocks, lists, and headers
- Code blocks include a "📋 Copy" button for easy code extraction
- The system maintains full conversation history for context-aware responses
- Rate limiting protection prevents API abuse with Semantic Scholar
- Error handling ensures graceful degradation when services are unavailable

## 📄 License

This project is part of the COM6104 Topics in Data Science and Artificial Intelligence course at Hang Seng University.