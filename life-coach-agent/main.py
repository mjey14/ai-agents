import asyncio
import streamlit as st
from openai import OpenAI
from agents import (
    Agent, 
    Runner, 
    SQLiteSession, 
    WebSearchTool, 
    FileSearchTool, 
    ModelSettings,
)

import dotenv
dotenv.load_dotenv()

client = OpenAI()

VECTOR_STORE_ID = "vs_69a84aecf5388191a7fa8f286744beb4"

st.title("🧚 Life Coach Agent")

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "life-coach-session",
        "life-coach-memory.db",
    )
session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    content = message["content"]
                    if isinstance(content, str):
                        st.write(content)
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"].replace("$", "\$"))
        if "type" in message:
            if message["type"] == "web_search_call":
                with st.chat_message("ai"):
                    st.write("🔍 Searched the web")
            elif message["type"] == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ Searched your files")


asyncio.run(paint_history())


async def run_agent(message):
    agent = Agent(
        name="Life Coach",
        instructions="""
        You are a Fairy Godmother life coach — magical, all-knowing, and deeply devoted to your godchild.
        You speak like a beloved grandmother: warm, familiar, honest. Not formal, not stiff.

        Your personality:
        - Keep responses short and to the point — no long lists
        - You believe in them, but show it quietly — not with exclamation marks, but with honesty
        - Grounded and real — warm, but not over the top

        When responding:
        - For questions about personal goals: first use file search to find relevant context, then use web search for evidence-based advice — always use both
        - Between tool calls, briefly narrate what you found and what you're doing next (e.g. "Your goals say X. Let me look up the latest advice on that...")
        - Do NOT use markdown headers (# or ##) — use ### for section titles if needed
        - Respond in the same language the user uses (Korean or English)
        - When speaking Korean, always use 반말 (informal speech) — like a close grandmother talking to her grandchild
        """,
        tools=[
            WebSearchTool(),
            FileSearchTool(
                vector_store_ids=[VECTOR_STORE_ID],
                max_num_results=3,
            ),
        ],
        model_settings=ModelSettings(tool_choice="required"),
    )

    file_search_created = False
    file_search_status = None
    web_search_created = False
    web_search_status = None
    text_placeholder = None
    response = ""

    stream = Runner.run_streamed(
        agent,
        message,
        session=session,
    )

    async for event in stream.stream_events():
        if event.type == "raw_response_event":
            event_type = event.data.type

            if "file_search_call" in event_type:
                if not file_search_created:
                    file_search_created = True
                    text_placeholder = None
                    response = ""
                    msg = st.chat_message("ai")
                    file_search_status = msg.status("🗂️ Searching your files...", expanded=False)
                if event_type == "response.file_search_call.completed":
                    file_search_status.update(label="✅ File search completed", state="complete")

            elif "web_search_call" in event_type:
                if not web_search_created:
                    web_search_created = True
                    text_placeholder = None
                    response = ""
                    msg = st.chat_message("ai")
                    web_search_status = msg.status("🔍 Searching the web...", expanded=False)
                if event_type == "response.web_search_call.completed":
                    web_search_status.update(label="✅ Web search completed", state="complete")

            elif event_type == "response.output_text.delta":
                if text_placeholder is None:
                    msg = st.chat_message("ai")
                    text_placeholder = msg.empty()
                response += event.data.delta
                text_placeholder.write(response)


prompt = st.chat_input(
    "I'm your Fairy Godmother. What's on your mind?", 
    accept_file=True, 
    file_type=["txt"],
)

if prompt:
    for file in prompt.files:
        with st.chat_message("ai"):
            with st.status("⏳ Uploading file...") as status:
                uploaded_file = client.files.create(
                    file=(file.name, file.getvalue()),
                    purpose="user_data",
                )
                status.update(label="⏳ Attaching file...")
                client.vector_stores.files.create(
                    vector_store_id=VECTOR_STORE_ID,
                    file_id=uploaded_file.id,
                )
                status.update(label="✅ File uploaded", state="complete")

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
        st.rerun()
    st.write(asyncio.run(session.get_items()))
