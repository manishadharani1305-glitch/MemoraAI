import streamlit as st
import json
import os
import requests
from datetime import datetime

MEMORY_FILE = "memora_memory.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:1b"


def load_memories():
    if not os.path.exists(MEMORY_FILE):
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_memories(memories):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memories, file, indent=4, ensure_ascii=False)


def add_memory(text):
    memories = load_memories()

    memory = {
        "id": len(memories) + 1,
        "text": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    memories.append(memory)
    save_memories(memories)


def delete_memory(memory_id):
    memories = load_memories()
    memories = [memory for memory in memories if memory["id"] != memory_id]

    for index, memory in enumerate(memories):
        memory["id"] = index + 1

    save_memories(memories)


def search_memory(query):
    memories = load_memories()
    query_words = query.lower().split()

    results = []

    for memory in memories:
        text = memory["text"].lower()

        score = sum(1 for word in query_words if word in text)

        if score > 0:
            results.append((score, memory))

    results.sort(key=lambda item: item[0], reverse=True)

    return [item[1] for item in results]


def ask_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()

        return None

    except:
        return None


def build_prompt(user_message, memories):
    memory_text = "\n".join(
        [f"- {memory['text']}" for memory in memories]
    )

    if not memory_text:
        memory_text = "No saved memories."

    return f"""
You are MemoraAI, a friendly local memory chatbot.

Use the user's saved memories when they are relevant.

Saved memories:
{memory_text}

User message:
{user_message}

Instructions:
- Give a natural and helpful answer.
- Use saved memories only when relevant.
- Do not invent personal information.
- If the user asks what you remember, clearly mention the saved memories.
- Keep the answer concise but useful.
"""


st.set_page_config(
    page_title="MemoraAI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 MemoraAI")
st.caption("A Local Memory Chatbot — A chatbot that remembers.")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("🧠 Memory Vault")

    memories = load_memories()

    st.metric("Saved Memories", len(memories))

    st.divider()

    st.subheader("Add a Memory")

    new_memory = st.text_area(
        "What should MemoraAI remember?"
    )

    if st.button("💾 Save Memory", use_container_width=True):
        if new_memory.strip():
            add_memory(new_memory.strip())
            st.success("Memory saved!")
            st.rerun()
        else:
            st.warning("Please enter something to remember.")

    st.divider()

    st.subheader("Stored Memories")

    memories = load_memories()

    if memories:
        for memory in memories:
            st.write(f"**{memory['id']}.** {memory['text']}")

            if st.button(
                f"Delete #{memory['id']}",
                key=f"delete_{memory['id']}"
            ):
                delete_memory(memory["id"])
                st.rerun()
    else:
        st.info("No memories saved yet.")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


user_message = st.chat_input(
    "Tell MemoraAI something..."
)

if user_message:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    relevant_memories = search_memory(user_message)

    prompt = build_prompt(
        user_message,
        relevant_memories
    )

    with st.chat_message("assistant"):

        with st.spinner("MemoraAI is thinking..."):

            answer = ask_ollama(prompt)

            if answer:
                final_answer = answer
            else:
                if relevant_memories:
                    memory_list = "\n".join(
                        [
                            f"• {memory['text']}"
                            for memory in relevant_memories[:5]
                        ]
                    )

                    final_answer = (
                        "I found these relevant memories:\n\n"
                        + memory_list
                    )
                else:
                    final_answer = (
                        "I couldn't connect to the local AI model. "
                        "You can still save memories using the Memory Vault."
                    )

            st.markdown(final_answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": final_answer
        }
    )