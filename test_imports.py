from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
import os

load_dotenv()
api = os.getenv("GROQ_API_KEY")
assert api, "Missing GROQ_API_KEY"

llm = ChatGroq(groq_api_key=api, model="llama-3.3-70b-versatile")
resp = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
print("✅ Test response:", resp.content)
