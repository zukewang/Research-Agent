# ui/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import markdown
from agent import ResearchAgent

app = FastAPI()

# 初始化 ResearchAgent（注意：不在此处立即初始化 MCP，而是在启动事件中）
research_agent = ResearchAgent()

@app.on_event("startup")
async def startup_event():
    """应用启动时异步初始化 MCP 工具"""
    await research_agent.initialize_mcp_tools()
    print("Agent initialized with tools:", [t.name for t in research_agent.tools])

# 挂载静态资源（假设 static/ 在项目根目录）
app.mount("/static", StaticFiles(directory=Path(__file__).parent.parent / "static"), name="static")

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(Path(__file__).parent.parent / "static" / "research.ico")

@app.get("/", response_class=HTMLResponse)
async def serve_chat_ui():
    # 前端 HTML 文件位于 ui/index.html（与本文件同目录）
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    else:
        # Fallback 简易界面
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head><title>Research Assistant</title></head>
        <body>
            <h2>Research Assistant AI</h2>
            <input id="msg" type="text" placeholder="Ask anything..." style="width:300px"/>
            <button onclick="send()">Send</button>
            <div id="response" style="margin-top:10px; padding:10px; background:#f0f0f0;"></div>
            <script>
                async function send() {
                    const msg = document.getElementById('msg').value;
                    const res = await fetch('/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: msg})
                    });
                    const data = await res.json();
                    document.getElementById('response').innerHTML = data.response;
                }
            </script>
        </body>
        </html>
        """)

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        history = data.get("history", [])
        
        if not history:
            return JSONResponse({"response": "No conversation history provided."})

        # 提取最新用户消息
        user_message = ""
        for msg in reversed(history):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").strip()
                break

        if not user_message:
            return JSONResponse({"response": "Please enter a message."})

        # 完全交由 agent 处理（注意：await 异步调用）
        bot_reply = await research_agent.run(user_message)

        # 渲染为 HTML
        html_output = markdown.markdown(
            bot_reply,
            extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.nl2br',
                'pymdownx.superfences'
            ]
        )
        return JSONResponse({"response": html_output})

    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "response": "Sorry, I encountered an error while processing your request."
        })