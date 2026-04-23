# tools/research_tools.py
from langchain_core.tools import tool
import requests
import time
import os
import glob
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from sentence_transformers import SentenceTransformer

class ExperimentRAG:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.documents = []
        self.embeddings = None
        self._load_and_index_logs()
    
    def _load_and_index_logs(self):
        """加载所有实验日志并创建向量索引"""
        log_files = list(self.log_dir.glob("*.log"))
        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取关键信息作为文档
                    doc = {
                        'filename': log_file.name,
                        'content': content,
                        'last_modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                    }
                    self.documents.append(doc)
            except Exception as e:
                print(f"Error reading {log_file}: {e}")
        
        if self.documents:
            # 创建文档文本用于嵌入
            doc_texts = [f"Experiment: {doc['filename']}\n{doc['content'][-1000:]}" 
                        for doc in self.documents]
            self.embeddings = self.model.encode(doc_texts)
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """基于语义相似度检索相关实验"""
        if not self.documents or self.embeddings is None:
            return []
        
        query_embedding = self.model.encode([query])
        similarities = np.dot(self.embeddings, query_embedding.T).flatten()
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.3:  # 相似度阈值
                results.append({
                    'document': self.documents[idx],
                    'similarity': float(similarities[idx])
                })
        return results


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
def check_experiment_status_rag(query: str) -> Dict[str, Any]:
    """RGA版本的实验状态检查"""
    rag_system = ExperimentRAG(Path("../experiments"))
    relevant_docs = rag_system.retrieve(query)
    
    if not relevant_docs:
        return {"error": f"No relevant experiments found for query: '{query}'"}
    
    # 格式化检索结果作为上下文
    context = ""
    for doc in relevant_docs[:2]:  # 取最相关的2个
        context += f"File: {doc['document']['filename']}\n"
        context += f"Last modified: {doc['document']['last_modified']}\n"
        context += f"Content snippet: {doc['document']['content'][-500:]}\n\n"
    
    return {"retrieved_context": context, "sources": [d['document']['filename'] for d in relevant_docs]}