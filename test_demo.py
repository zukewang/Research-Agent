# test_demo.py
import asyncio
from agent import ResearchAgent

async def main():
    agent = ResearchAgent()
    # 显式初始化 MCP（可选，因为 run 会自动初始化）
    await agent.initialize_mcp_tools()
    
    print("🚀 Starting Research Assistant Demo...\n")
    
    print(await agent.run("What is a transformer?"))
    print(await agent.run("Find recent papers on vision transformers."))
    print(await agent.run("Summarize the first paper you found."))
    print(await agent.run("please write a python code for vision transformer"))
    
    print("✅ Demo completed. Check ~/experiments/ for log files.")
    
    print(await agent.run("What is the status of my experiment on ViT Transformer?"))
    print(await agent.run("What about diffusion models?"))
    print(await agent.run("Is the LLM fine-tuning done?"))
    print(await agent.run("How did the loss change during the ViT Transformer experiment?"))
    print(await agent.run("What was the final accuracy of my ViT experiment?"))

if __name__ == "__main__":
    asyncio.run(main())