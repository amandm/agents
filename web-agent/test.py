from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
# from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv('GOOGLE_API_KEY')
os.environ["TAVILY_API_KEY"] = os.getenv('TAVILY_API_KEY')
os.environ["OPENAI_API_KEY"]  = os.getenv('OPENAI_API_KEY')
os.environ["LANGSMITH_API_KEY"]  = os.getenv('LANGSMITH_API_KEY')

async def main():
    agent = Agent(
        task="Go to Reddit, search for 'browser-use' in the search bar, click on the first post and return the first comment.",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    result = await agent.run()
    print(result)

asyncio.run(main())