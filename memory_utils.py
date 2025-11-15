# memory_utils.py
class SimpleMemory:
    def __init__(self):
        self.chat_history = []

    def load_memory_variables(self, _):
        history = "\n".join([
            f"User: {m['user']}\nAssistant: {m['assistant']}"
            for m in self.chat_history
        ])
        return {"history": history}

    def save_context(self, inputs, outputs):
        user_input = inputs.get("input", "")
        assistant_output = outputs.get("output", "")
        self.chat_history.append({
            "user": user_input,
            "assistant": assistant_output
        })
