# app.py — Nova (Agentic Hybrid RAG Chatbot) — Phase (updated)
from __future__ import annotations
import os
import uuid
import tempfile
from dotenv import load_dotenv
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# local modules
from memory_graph import (
    load_history,
    save_turn,
    clear_history,
    save_profile,
    get_profile,
    save_fact,
    get_facts,
)
from rag_utils import RAGIndex
import agent_hub

# === Setup ===
load_dotenv()
st.set_page_config(page_title="Nova — Agentic Hybrid RAG Chatbot", page_icon="🤖", layout="wide")

# Directories (option A: tmp_uploads)
TMP_DIR = os.path.join(os.getcwd(), "tmp_uploads")
CHROMA_DIR = os.path.join(TMP_DIR, "chroma_db")
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)

# --- API / LLM setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    st.error("⚠️ Missing GROQ_API_KEY in .env. Add GROQ_API_KEY and restart.")
    st.stop()

llm = ChatGroq(groq_api_key=GROQ_API_KEY, model=MODEL)

# --- Initialize RAG + memory ---
rag = RAGIndex(persist_dir=CHROMA_DIR)

# session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("Nova — Agentic Hybrid RAG Chatbot")

# --- Sidebar ---
with st.sidebar:
    st.header("Session Controls")
    if st.button("🧹 Clear conversation (current thread)"):
        clear_history(st.session_state.thread_id)
        st.session_state.chat_history = []
        st.rerun()

    st.markdown("### Agent Mode")
    agent_mode = st.checkbox("Enable Agent Mode (planner + tools)", value=True)

    st.markdown("### Memory (Profiles)")
    saved_name = get_profile("name") or ""
    name_inp = st.text_input("Stored name (optional)", value=saved_name)
    if name_inp.strip() and name_inp.strip() != saved_name:
        save_profile("name", name_inp.strip())
        st.success(f"Saved name: {name_inp.strip()}")

    if st.button("🧠 Show current memory"):
        st.write("**Name:**", get_profile("name"))
        st.write("**Facts:**", get_facts())

    st.markdown("### RAG / Documents")
    if rag.count() > 0:
        st.success(f"RAG Ready — {rag.count()} chunks stored")
    else:
        st.info("No indexed documents found. Upload PDFs below to enable RAG retrieval.")

    uploaded = st.file_uploader("📄 Upload PDFs (temporary)", type=["pdf"], accept_multiple_files=True)
    if uploaded:
        for file in uploaded:
            # Save to tmp_uploads with a safe unique name (so it does not land in repo root)
            uid = uuid.uuid4().hex[:8]
            safe_name = f"{os.path.splitext(file.name)[0]}_{uid}.pdf"
            dest_path = os.path.join(TMP_DIR, safe_name)
            with open(dest_path, "wb") as f:
                f.write(file.read())
            # Index the file (this writes into the chroma DB in CHROMA_DIR)
            try:
                rag.load_pdf(dest_path)
                st.success(f"Uploaded & indexed: {file.name}")
            except Exception as e:
                st.error(f"Indexing failed for {file.name}: {e}")

    if st.button("🗑️ Clear uploaded tmp files"):
        # clear tmp uploads but keep chroma_db (user may want to re-index later)
        for fn in os.listdir(TMP_DIR):
            p = os.path.join(TMP_DIR, fn)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass
        st.success("Temporary uploads cleared.")

# --- Persona / prompt helper ---
BASE_PERSONA = (
    "You are Nova, a concise, professional assistant. Answer clearly and prefer factual, sourced answers."
)

def build_context_prompt(user_text: str, stored_name: str, rag_context: str, memory_facts: list):
    greetings = ["hi", "hello", "hey", "good morning", "good evening"]
    is_greeting = any(user_text.lower().startswith(g) for g in greetings)

    include_personal = not is_greeting and any(
        kw in user_text.lower()
        for kw in ["friend", "teacher", "college", "project", "experience", "my", "name"]
    )

    context_prompt = BASE_PERSONA + "\n\n"
    if include_personal and stored_name:
        context_prompt += f"The user's name is {stored_name}. "
    if include_personal and memory_facts:
        facts_str = "; ".join([f"{f[0]}: {f[1]}" for f in memory_facts])
        if facts_str:
            context_prompt += f"Relevant memory facts: {facts_str}. "
    if rag_context:
        context_prompt += f"\nDocument context (from uploaded files):\n{rag_context}\n"
    if is_greeting:
        context_prompt += "\nRespond briefly and naturally to greetings.\n"
    context_prompt += f"\nUser: {user_text}\n"
    return context_prompt

# --- Load history (display) ---
history: list[BaseMessage] = load_history(st.session_state.thread_id)
for m in history:
    role = "user" if isinstance(m, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(m.content)

# --- Chat Input ---
user_text = st.chat_input("Ask anything…")

if user_text:
    with st.chat_message("user"):
        st.markdown(user_text)

    # small lightweight fact saving (quick workflows)
    lower = user_text.lower()
    try:
        if "friend" in lower and "name is" in lower:
            name = user_text.split("name is")[-1].strip().split()[0]
            save_fact("friend", "friend_name", name)
            reply = f"Got it — I’ll remember your friend's name is {name}."
            with st.chat_message("assistant"):
                st.markdown(reply)
            save_turn(st.session_state.thread_id, user_text, reply)
            st.stop()

        if "teacher" in lower and ("is" in lower or "sir" in lower):
            teacher = user_text.split("is")[-1].strip() if "is" in lower else user_text
            save_fact("teacher", "teacher_name", teacher)
            reply = f"Thanks — I’ll remember that {teacher} is your teacher."
            with st.chat_message("assistant"):
                st.markdown(reply)
            save_turn(st.session_state.thread_id, user_text, reply)
            st.stop()
    except Exception as e:
        # fail-safe
        st.warning(f"Lightweight memory handling error: {e}")

    # prepare contexts
    stored_name = get_profile("name")
    facts = get_facts() or []
    context_docs = rag.query(user_text, top_k=3) if rag.count() > 0 else []
    rag_context = " ".join([doc for doc, _ in context_docs]) if context_docs else ""

    # Agent mode
    if agent_mode:
        streamer = agent_hub.run_agent(
            user_text=user_text,
            llm=llm,
            rag_index=rag,
            get_profile_fn=get_profile,
            get_facts_fn=get_facts,
            top_k=3,
        )
        with st.chat_message("assistant"):
            placeholder = st.empty()
            accumulated = ""
            try:
                for chunk in streamer:
                    accumulated += chunk
                    placeholder.markdown(accumulated + "▌")
                placeholder.markdown(accumulated)
                save_turn(st.session_state.thread_id, user_text, accumulated)
            except Exception as e:
                st.error(f"❌ Agent error: {e}")
    else:
        # fallback plain RAG prompt
        prompt = build_context_prompt(user_text, stored_name, rag_context, facts)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            streamed = ""
            try:
                for chunk in llm.stream(prompt):
                    if hasattr(chunk, "content"):
                        streamed += chunk.content
                    else:
                        streamed += str(chunk)
                    placeholder.markdown(streamed + "▌")
                placeholder.markdown(streamed)
                save_turn(st.session_state.thread_id, user_text, streamed)
            except Exception as e:
                st.error(f"❌ Streaming error: {e}")
