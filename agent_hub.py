"""
agent_hub.py — Clean Version (No "no document used" messages)
"""

from typing import Callable, Dict, Iterable, List, Tuple, Optional
import ast
import re
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------
# Safe math evaluator
# ---------------------------------------------------------
class _SafeMathVisitor(ast.NodeVisitor):
    ALLOWED = (
        ast.Expression, ast.BinOp, ast.UnaryOp,
        ast.Constant, ast.Add, ast.Sub,
        ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.FloorDiv, ast.USub, ast.UAdd,
        ast.Load, ast.Tuple, ast.List
    )

    def generic_visit(self, node):
        if not isinstance(node, self.ALLOWED):
            raise ValueError(f"Disallowed AST node: {type(node).__name__}")
        super().generic_visit(node)


def safe_math_eval(expr: str):
    try:
        parsed = ast.parse(expr, mode="eval")
        _SafeMathVisitor().visit(parsed)
        return eval(compile(parsed, "<safe_math>", "eval"), {"__builtins__": {}}, {})
    except Exception as e:
        raise ValueError(f"Invalid math expression: {e}")


# ---------------------------------------------------------
# RAG + Memory tool wrappers
# ---------------------------------------------------------
def rag_query_fn(rag_index, query: str, top_k: int = 3):
    if rag_index is None:
        return []
    try:
        res = rag_index.query(query, top_k=top_k) or []
        cleaned = []
        for item in res:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                cleaned.append(item)
            else:
                cleaned.append((str(item), 0.0))
        return cleaned
    except Exception:
        return []


def memory_lookup_fn(get_profile, get_facts, query: str):
    mem = {}
    try:
        mem["name"] = get_profile("name") if get_profile else None
        mem["facts"] = get_facts() if get_facts else []
    except Exception:
        pass
    return mem


# ---------------------------------------------------------
# Planner for tool usage
# ---------------------------------------------------------
def _decide_tools(user_text: str, docs_exist: bool):
    t = user_text.lower()

    use_rag = any(k in t for k in ["resume", "pdf", "document", "summarize", "experience", "projects"])
    if docs_exist:
        use_rag = True

    use_memory = any(k in t for k in ["my", "profile", "remember", "name", "teacher", "friend"])
    use_math = any(k in t for k in ["calculate", "compute", "+", "-", "*", "/", "^"])

    return {"use_rag": use_rag, "use_memory": use_memory, "use_math": use_math}


# ---------------------------------------------------------
# Prompt Creation (CLEANED)
# ---------------------------------------------------------
def _compose_prompt(user_text: str, mem: dict, rag_excerpt: str, math_answer: Optional[object], tools: dict):
    lines = [
        "You are Nova, a helpful and factual AI assistant.",
        "",
    ]

    # Basic memory usage (no unnecessary sentences)
    if mem.get("name"):
        lines.append(f"User name: {mem['name']}.")
    if mem.get("facts"):
        fact_str = "; ".join([f"{k}: {v}" for k, v in mem["facts"]])
        lines.append(f"Memory facts: {fact_str}")

    # Include RAG context ONLY if available
    if rag_excerpt:
        lines.append("\nRelevant document context:\n" + rag_excerpt)

    if math_answer is not None:
        lines.append(f"\nMath result: {math_answer}")

    lines.append("\nUser: " + user_text)
    lines.append("Provide the best possible answer without mentioning tool usage unless helpful.")

    return "\n".join(lines)


# ---------------------------------------------------------
# Main Agent Runner
# ---------------------------------------------------------
def run_agent(
    user_text: str,
    llm,
    rag_index,
    get_profile_fn,
    get_facts_fn,
    top_k: int = 3,
) -> Iterable[str]:

    # Determine if docs exist
    try:
        docs_exist = rag_index.count() > 0
    except:
        docs_exist = False

    tools = _decide_tools(user_text, docs_exist)

    # Memory
    mem = memory_lookup_fn(get_profile_fn, get_facts_fn, user_text) if tools["use_memory"] else {}

    # RAG
    rag_results, rag_excerpt = [], ""
    if tools["use_rag"]:
        rag_results = rag_query_fn(rag_index, user_text, top_k)
        if rag_results:
            rag_excerpt = "\n\n".join([txt for txt, score in rag_results])

    # Math
    math_answer = None
    if tools["use_math"]:
        expr = user_text.lower().replace("calculate", "").replace("what is", "").strip()
        try:
            math_answer = safe_math_eval(expr)
        except:
            math_answer = None

    # Compose prompt
    prompt = _compose_prompt(
        user_text=user_text,
        mem=mem,
        rag_excerpt=rag_excerpt,
        math_answer=math_answer,
        tools=tools
    )

    # Stream output
    try:
        for chunk in llm.stream(prompt):
            if hasattr(chunk, "content"):
                yield chunk.content
            else:
                yield str(chunk)
    except Exception as e:
        yield f"[Error: {e}]"
