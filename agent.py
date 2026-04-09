# agent.py
import asyncio
from typing import Annotated, Literal, List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from typing_extensions import TypedDict
from langchain_mcp_adapters.client import MultiServerMCPClient

# === 状态定义 ===
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class ResearchAgent:
    def __init__(self):
        self.llm = ChatOllama(model="qwen3:8b", temperature=0.7)
        
        # 纯内存长时记忆
        self.long_term_memory: List[str] = []
        
        # 内置 memory 工具
        self.tools = [
            self._create_add_memory_tool(),
            self._create_search_memory_tool(),
        ]
        
        self._mcp_initialized = False  # 标记是否已加载 MCP 工具
        self._lock = asyncio.Lock()
        
        # 先绑定内置工具，后续初始化 MCP 后重新绑定
        self._bind_tools()
        
        # 构建状态图（使用当前 llm_with_tools）
        builder = StateGraph(State)
        builder.add_node("model", self._call_model)
        builder.add_node("tools", self._call_tool)
        builder.add_edge(START, "model")
        builder.add_conditional_edges("model", self._should_continue)
        builder.add_edge("tools", "model")
        self.graph = builder.compile(checkpointer=InMemorySaver())

    # === 内存记忆工具 ===
    def _create_add_memory_tool(self):
        @tool
        def add_memory(item: str) -> str:
            """Add a fact to long-term memory."""
            stripped = item.strip()
            if stripped and stripped not in self.long_term_memory:
                self.long_term_memory.append(stripped)
                return f"✅ Remembered: {stripped[:50]}..."
            return "❌ Empty or duplicate item."
        return add_memory

    def _create_search_memory_tool(self):
        @tool
        def search_memory(query: str) -> str:
            """Search long-term memory by keyword."""
            if not self.long_term_memory:
                return "No memories stored."
            matches = [f for f in self.long_term_memory if query.lower() in f.lower()]
            if matches:
                return "Relevant memories:\n" + "\n".join(matches[:3])
            return "No relevant memories found."
        return search_memory

    # === 工具绑定 ===
    def _bind_tools(self):
        """绑定当前 tools 到 llm"""
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    # === 异步初始化 MCP 工具 ===
    async def initialize_mcp_tools(self):
        async with self._lock:
            if self._mcp_initialized:
                return
            try:
                # 创建 client 实例（不使用上下文管理器）
                client = MultiServerMCPClient(
                    {
                        "research_assistant": {
                            "transport": "streamable_http",
                            "url": "http://localhost:30000/mcp",
                        }
                    }
                )
                # 直接调用 get_tools()
                mcp_tools = await client.get_tools()
                if mcp_tools:
                    self.tools.extend(mcp_tools)
                    self._bind_tools()
                    print(f"✅ Loaded MCP tools: {[t.name for t in mcp_tools]}")
                else:
                    print("⚠️ No MCP tools retrieved.")
                self._mcp_initialized = True
            except Exception as e:
                print(f"❌ MCP connection error: {e}")

    # === 确保在调用模型前 MCP 已初始化 ===
    async def ensure_mcp_initialized(self):
        """确保 MCP 工具已初始化（供外部调用）"""
        if not self._mcp_initialized:
            await self.initialize_mcp_tools()

    # === 图节点函数 ===
    def _call_model(self, state: State, config: RunnableConfig) -> dict:
        system_prompt = SystemMessage(
            content="""You are a research assistant with access to tools. Follow these rules strictly:
1. When the user asks about the status of an experiment (e.g., "What is the status of my experiment on ...?" or "Have I run experiments on ...?"), you MUST call the 'check_experiment_status' tool with the relevant paper title or keywords.
2. The 'check_experiment_status' tool will return detailed information from local experiment logs, including status, filename, last modified time, and metrics like final accuracy, final loss, accuracy progression, etc. Use these details to answer the user.
3. Do NOT say you cannot access local logs or that you lack direct access. You have the tool to do it.
4. Only use 'search_memory' as a fallback if no file-based evidence is found.
5. For academic paper queries, use 'lookup_paper' to search for papers.
6. Always prioritize using the appropriate tool before generating a final answer.

Example:
User: "What is the status of my ViT experiment?"
Assistant: [Calls check_experiment_status with paper_title="ViT Transformer"]"""
        )
        enhanced_messages = [system_prompt] + state["messages"]
        response = self.llm_with_tools.invoke(enhanced_messages, config)
        return {"messages": [response]}

    async def _call_tool(self, state: State) -> dict:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            tool_call = last_msg.tool_calls[0]
            tool_name = tool_call["name"]
            tool_map = {t.name: t for t in self.tools}
            if tool_name in tool_map:
                # 异步调用工具
                result = await tool_map[tool_name].ainvoke(tool_call["args"])
                
                # 针对 check_experiment_status 工具进行友好格式化
                if tool_name == "check_experiment_status" and isinstance(result, dict):
                    if "error" in result:
                        content = f"❌ {result['error']}"
                    else:
                        # 基础信息
                        content = f"Experiment status: {result.get('status', 'Unknown')}. "
                        content += f"Last modified: {result.get('last_modified', 'N/A')}. "
                        content += f"File: {result.get('filename', 'N/A')}."
                        
                        # 添加解析出的详细指标
                        details = []
                        if "final_accuracy" in result:
                            details.append(f"final accuracy: {result['final_accuracy']:.1%}")
                        if "final_loss" in result:
                            details.append(f"final loss: {result['final_loss']:.2f}")
                        if "accuracy_start" in result and "accuracy_end" in result:
                            details.append(f"accuracy improved from {result['accuracy_start']:.1%} to {result['accuracy_end']:.1%}")
                        if "loss_start" in result and "loss_end" in result:
                            details.append(f"loss decreased from {result['loss_start']:.2f} to {result['loss_end']:.2f}")
                        if "epochs_completed" in result:
                            details.append(f"trained for {result['epochs_completed']} epochs")
                        
                        if details:
                            content += "\n" + " ".join(details)
                else:
                    # 其他工具直接返回字符串形式
                    content = str(result)
                
                return {
                    "messages": [
                        ToolMessage(
                            content=content,
                            tool_call_id=tool_call["id"]
                        )
                    ]
                }
        return {"messages": []}

    def _should_continue(self, state: State) -> Literal["tools", "__end__"]:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        return END  # type: ignore

    async def run(self, user_input: str, thread_id: str = "default") -> str:
        # 确保 MCP 已初始化（在第一次调用时）
        await self.ensure_mcp_initialized()
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        response = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            config
        )
        final_message = response["messages"][-1]
        return final_message.content if isinstance(final_message.content, str) else str(final_message.content)