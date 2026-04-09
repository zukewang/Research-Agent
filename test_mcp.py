import asyncio
import traceback
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    try:
        client = MultiServerMCPClient(
            {"test": {"transport": "streamable_http", "url": "http://localhost:30000/mcp"}}
        )
        tools = await client.get_tools()
        print("✅ Tools:", [t.name for t in tools])
    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())