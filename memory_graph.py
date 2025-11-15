# memory_graph.py
import sqlite3, os

DB_PATH = "memory.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id TEXT,
        role TEXT,
        content TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        label TEXT,
        value TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# ---------------- History ----------------
def save_turn(thread_id, human, ai):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO chat_history (thread_id, role, content) VALUES (?, ?, ?)", (thread_id, "user", human))
    cur.execute("INSERT INTO chat_history (thread_id, role, content) VALUES (?, ?, ?)", (thread_id, "assistant", ai))
    conn.commit()
    conn.close()

def load_history(thread_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM chat_history WHERE thread_id=? ORDER BY id", (thread_id,))
    rows = cur.fetchall()
    conn.close()
    from langchain_core.messages import HumanMessage, AIMessage
    return [HumanMessage(c) if r == "user" else AIMessage(c) for r, c in rows]

def clear_history(thread_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_history WHERE thread_id=?", (thread_id,))
    conn.commit()
    conn.close()

# ---------------- Profile ----------------
def save_profile(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_profile(key):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM profile WHERE key=?", (key,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res else None

# ---------------- Facts (New Entity Memory) ----------------
def save_fact(category, label, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO facts (category, label, value) VALUES (?, ?, ?)", (category, label, value))
    conn.commit()
    conn.close()

def get_facts(category=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if category:
        cur.execute("SELECT label, value FROM facts WHERE category=?", (category,))
    else:
        cur.execute("SELECT category, label, value FROM facts")
    rows = cur.fetchall()
    conn.close()
    return rows

def clear_facts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM facts")
    conn.commit()
    conn.close()
