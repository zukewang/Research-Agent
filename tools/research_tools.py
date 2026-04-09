# tools/research_tools.py
from langchain_core.tools import tool
import requests
import time
import os
import glob
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


def check_log_dir() -> Dict[str, Any]:
    """
    Check the log directory and print its status.
    
    Returns:
        Dict[str, Any]: A dictionary containing information about the log directory.
    """
    log_dir = Path("../experiments").expanduser()
    return {
        "log_directory": str(log_dir),
        "exists": log_dir.exists(),
        "absolute_path": str(log_dir.resolve())
    }


@tool
def lookup_paper(query: str) -> Dict[str, Any]:
    """
    Search for academic papers using Semantic Scholar API.
    
    Args:
        query (str): The search query for academic papers.
        
    Returns:
        Dict[str, Any]: A dictionary containing either:
            - 'papers': list of formatted paper dicts (if successful)
            - 'error': error message string (if failed)
            - 'message': informational message (e.g., no results)
    """
    if not query.strip():
        return {
            "error": "Missing required argument: 'query'"
        }

    # 防高频请求
    time.sleep(1.5)

    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": 3,
        "fields": "title,authors,abstract,year,url"
    }
    headers = {
        "User-Agent": "ResearchAssistant/1.0 (Academic Tool)"
    }

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                api_url,
                params=params,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                papers_data = data.get("data", [])
                
                if not papers_data:
                    return {
                        "message": f"No relevant papers found for query: '{query}'"
                    }

                formatted_papers = []
                for paper in papers_data:
                    formatted_papers.append({
                        "title": paper.get("title", "N/A"),
                        "authors": [a["name"] for a in paper.get("authors", [])[:3]],
                        "year": paper.get("year", None),
                        "abstract": (paper.get("abstract") or "No abstract.")[:300] + "...",
                        "url": paper.get("url", "#")
                    })
                
                return {
                    "papers": formatted_papers
                }

            elif response.status_code == 429:
                wait_time = 3 + attempt * 2
                time.sleep(wait_time)
                continue

            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.reason}"
                }

        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(3)
                continue
            return {
                "error": f"Network error after retries: {str(e)}"
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}"
            }

    return {
        "error": "Failed to fetch papers after multiple retries (likely rate-limited)."
    }


@tool
def check_experiment_status(paper_title: str) -> Dict[str, Any]:
    """
    Check the status of a local machine learning experiment by searching log files 
    in the 'experiments/' directory. The tool matches log filenames containing keywords 
    from the paper title (e.g., 'diffusion', 'vit'). Returns structured status info.
    
    Args:
        paper_title (str): Title or keywords of the paper associated with the experiment.
        
    Returns:
        Dict[str, Any]: A dictionary containing either:
            - 'filename', 'status', 'recent_output', etc. (if found)
            - 'error' (if not found or read failed)
    """
    if not paper_title.strip():
        return {
            "error": "Missing required argument: 'paper_title'"
        }

    # 确定日志目录（相对于项目根目录）
    log_dir_info = check_log_dir()
    if not log_dir_info['exists']:
        return {
            "error": f"Log directory does not exist: {log_dir_info['absolute_path']}"
        }

    log_dir = Path(log_dir_info['absolute_path'])
    log_dir.mkdir(parents=True, exist_ok=True)

    # 构建通配符模式：支持多关键词（如 "diffusion models" → *diffusion*models*）
    normalized = "".join(c if c.isalnum() or c.isspace() else "" for c in paper_title)
    keywords = normalized.split()
    pattern_str = "*".join(keywords)
    pattern = log_dir / f"*{pattern_str}*.log"

    log_files = glob.glob(str(pattern))

    # 宽松匹配：逐个关键词尝试
    if not log_files:
        for kw in keywords:
            pattern = log_dir / f"*{kw}*.log"
            log_files = glob.glob(str(pattern))
            if log_files:
                break

    if not log_files:
        return {
            "error": f"No experiment logs found for '{paper_title}' in directory: {log_dir}",
            "directory": str(log_dir),
            "keywords_tried": keywords
        }

    latest_log = max(log_files, key=os.path.getmtime)

    # 读取日志内容
    try:
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        last_lines = lines[-10:] if len(lines) >= 10 else lines
        last_content = "".join(last_lines)
        last_content_lower = last_content.lower()

        # 判断状态
        if "training completed" in last_content_lower or "final accuracy" in last_content_lower:
            status = "✅ COMPLETED"
        elif "error" in last_content_lower or "exception" in last_content_lower:
            status = "❌ FAILED"
        else:
            status = "🔄 RUNNING"

        snippet = last_content.strip()[-300:]
        dt = datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime("%Y-%m-%d %H:%M")

        return {
            "filename": os.path.basename(latest_log),
            "last_modified": dt,
            "status": status,
            "location": str(latest_log),
            "recent_output": snippet
        }

    except Exception as e:
        return {
            "error": f"Failed to read log file: {str(e)}"
        }