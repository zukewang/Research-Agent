from fastmcp import FastMCP
import requests
import time
import os
import glob
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import re

mcp = FastMCP("Research Assistant MCP Server")

# 工具1：论文检索
@mcp.tool 
def lookup_paper(query: str) -> Dict[str, Any]:
    """
    Search for academic papers using Semantic Scholar API.
    Args:
        query: Keyword for paper search (e.g., "LLM quantization 2023")
    Returns:
        Formatted paper information including title, authors, year, etc.
    """
    if not query.strip():
        return {"error": "Missing required argument: 'query'"}

    time.sleep(1.5)
    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {"query": query, "limit": 3, "fields": "title,authors,abstract,year,url"}
    headers = {"User-Agent": "ResearchAssistant/1.0"}

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                papers_data = data.get("data", [])
                if not papers_data:
                    return {"message": f"No relevant papers found for query: '{query}'"}

                formatted_papers = []
                for paper in papers_data:
                    formatted_papers.append({
                        "title": paper.get("title", "N/A"),
                        "authors": [a["name"] for a in paper.get("authors", [])[:3]],
                        "year": paper.get("year", None),
                        "abstract": (paper.get("abstract") or "No abstract.")[:300] + "...",
                        "url": paper.get("url", "#")
                    })
                return {"papers": formatted_papers}

            elif response.status_code == 429:
                time.sleep(3 + attempt * 2)
                continue
            else:
                return {"error": f"HTTP {response.status_code}: {response.reason}"}

        except requests.RequestException as e:
            if attempt < max_retries:
                time.sleep(3)
                continue
            return {"error": f"Network error after retries: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    return {"error": "Failed to fetch papers after multiple retries."}

# 工具2：实验日志状态检查
@mcp.tool
def check_experiment_status(paper_title: str) -> Dict[str, Any]:
    """
    Search local experiment log files to check if an experiment was run. This is more reliable than memory.
    Args:
        paper_title: Title/keyword of the paper related to the experiment
    Returns:
        Experiment status, log file path, last modified time, etc.
    """
    if not paper_title.strip():
        return {"error": "Missing required argument: 'paper_title'"}

    # 定义实验日志目录（自动创建）
    log_dir = Path(__file__).parent / "experiments"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 规范化关键词，匹配日志文件
    normalized = "".join(c if c.isalnum() or c.isspace() else "" for c in paper_title)
    keywords = normalized.split()
    
    # 优先匹配多关键词组合，失败则匹配单个关键词
    log_files = []
    if keywords:
        pattern = log_dir / f"*{'*'.join(keywords)}*.log"
        log_files = glob.glob(str(pattern))
        if not log_files:
            for kw in keywords:
                pattern = log_dir / f"*{kw}*.log"
                log_files = glob.glob(str(pattern))
                if log_files:
                    break

    if not log_files:
        return {
            "error": f"No experiment logs found for '{paper_title}'",
            "directory": str(log_dir),
            "keywords_tried": keywords
        }

    # 获取最新修改的日志文件
    latest_log = max(log_files, key=os.path.getmtime)
    last_modified = datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime("%Y-%m-%d %H:%M:%S")

    # 解析日志状态
    try:
        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
        
        if "training completed" in content or "final accuracy" in content:
            status = "✅ COMPLETED"
        elif "error" in content or "exception" in content:
            status = "❌ FAILED (Error in log)"
        elif "running" in content or "in progress" in content:
            status = "⏳ RUNNING"
        else:
            status = "ℹ️ UNKNOWN (No status keyword found)"
            
        final_accuracy = None
        final_loss = None
        epochs_completed = None
        accuracy_start = None
        accuracy_end = None
        loss_start = None
        loss_end = None
        
        acc_match = re.search(r'final accuracy:\s*([\d.]+)%', content)
        if acc_match:
            final_accuracy = float(acc_match.group(1)) / 100.0
            
        epoch_pattern = r'epoch\s+(\d+)/(\d+):\s*loss=([\d.]+),\s*acc=([\d.]+)'
        epochs = re.findall(epoch_pattern, content, re.IGNORECASE)
        
        if epochs:
            # 总 epoch 数（从最后一条记录获取分母）
            epochs_completed = int(epochs[-1][1])
            # 第一个 epoch 的指标
            accuracy_start = float(epochs[0][3])
            loss_start = float(epochs[0][2])
            # 最后一个 epoch 的指标
            accuracy_end = float(epochs[-1][3])
            loss_end = float(epochs[-1][2])

        # 如果没有单独 final_accuracy 行，则使用最后一个 epoch 的准确率作为最终准确率
        if final_accuracy is None and accuracy_end is not None:
            final_accuracy = accuracy_end
            
        result = {
            "status": status,
            "filename": os.path.basename(latest_log),
            "last_modified": last_modified,
            "directory": str(log_dir),
            "matched_keywords": keywords,
        }
        
        # 添加解析出的指标（如果存在）
        if final_accuracy is not None:
            result["final_accuracy"] = final_accuracy
        if final_loss is not None:
            result["final_loss"] = final_loss
        if epochs_completed is not None:
            result["epochs_completed"] = epochs_completed
        if accuracy_start is not None:
            result["accuracy_start"] = accuracy_start
        if accuracy_end is not None:
            result["accuracy_end"] = accuracy_end
        if loss_start is not None:
            result["loss_start"] = loss_start
        if loss_end is not None:
            result["loss_end"] = loss_end

        return result

    except Exception as e:
        return {"error": f"Failed to read log file: {str(e)}", "filename": os.path.basename(latest_log)}
    
if __name__ == "__main__":
    # 使用 streamable-http 传输，监听端口 30000（与 start.bat 一致）
    mcp.run(transport="streamable-http", port=30000)