import dotenv
dotenv.load_dotenv()

import asyncio
import json
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool, ModelSettings

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
                        st.write(message["content"][0]["text"])
        if "type" in message:
            if message["type"] == "web_search_call":
                with st.chat_message("ai"):
                    st.write("✅ Searched the web")


asyncio.run(paint_history())


def update_status(status_container, event_data):
    if event_data.type == "response.web_search_call.in_progress":
        status_container.update(label="🔍 Searching the web...", state="running")


async def run_agent(message):
    agent = Agent(
        name="Life Coach",
        instructions="""
        You are a Fairy Godmother life coach — like a beloved grandmother or great-aunt
        who knows your user inside out and wants nothing more than to see them shine.

        Your personality:
        - Speak like you're giving heartfelt advice to your favourite grandchild — warm,
          familiar, close. Not formal, not stiff.
        - Keep responses short and to the point. No long lists. Just what they need to hear.
        - You believe in them, but you show it quietly — not with exclamation marks, but with honesty.
        - Grounded and real. Warm, but not over the top.

        When responding:
        - Use web search to find the latest evidence-based advice
        - Do NOT use markdown headers (# or ##) — use ### for section titles if needed, and **bold** for emphasis
        - Respond in the same language the user uses (Korean or English)
        - When speaking Korean, always use 반말 (informal speech) — like a close grandmother talking to her grandchild
        """,
        tools=[WebSearchTool()],
        model_settings=ModelSettings(tool_choice="required"),
    )

    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(
            agent,
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    raw_query = event.item.raw_item.action.query
                    query = json.loads(f'"{raw_query}"')
                    status_container.update(label=f'✅ Searched: "{query}"', state="complete")
            if event.type == "raw_response_event":
                update_status(status_container, event.data)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)


prompt = st.chat_input("무엇이든 물어보세요. 함께 해결해 드릴게요!")

if prompt:
    with st.chat_message("human"):
        st.write(prompt)
    asyncio.run(run_agent(prompt))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
        st.rerun()
    st.write(asyncio.run(session.get_items()))
