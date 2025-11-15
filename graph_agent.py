# graph_agent.py
from __future__ import annotations
from typing import TypedDict, List
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from search_tool import web_search

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def chat_node(state: ChatState, llm: ChatGroq) -> ChatState:
    ai_msg = llm.invoke(state["messages"])
    return {"messages": [ai_msg]}

def search_node(state: ChatState, llm: ChatGroq) -> ChatState:
    user_query = state["messages"][-1].content
    search_data = web_search(user_query)
    summary_prompt = f"Summarize and answer using these search results for '{user_query}':\n\n{search_data}"
    ai_msg = llm.invoke([HumanMessage(content=summary_prompt)])
    return {"messages": [ai_msg]}

def router(state: ChatState) -> str:
    msg = state["messages"][-1].content.lower()
    triggers = ["today", "latest", "news", "update", "weather", "who won", "current", "live", "trend", "price"]
    return "search" if any(k in msg for k in triggers) else "chat"

def build_graph(llm: ChatGroq):
    graph = StateGraph(ChatState)
    graph.add_node("chat", lambda s: chat_node(s, llm))
    graph.add_node("search", lambda s: search_node(s, llm))
    graph.add_conditional_edges(START, router, {"chat": "chat", "search": "search"})
    graph.add_edge("chat", END)
    graph.add_edge("search", END)
    return graph.compile()
