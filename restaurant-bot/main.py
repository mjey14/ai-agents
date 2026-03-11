import dotenv
dotenv.load_dotenv()

import asyncio
import json
import os
import streamlit as st
from agents import Runner, SQLiteSession, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from my_agents.agents import triage_agent

st.title("🍽️ Restaurant Bot")

HANDOFF_MESSAGES = {
    "Menu Agent": "🥗 메뉴 담당자에게 연결합니다...",
    "Order Agent": "📋 주문 담당자에게 연결합니다...",
    "Reservation Agent": "📅 예약 담당자에게 연결합니다...",
    "Complaints Agent": "💬 CS 담당자에게 연결합니다...",
}

AGENT_HISTORY_FILE = "agent_history.json"


def agent_display_name(agent_name):
    return agent_name.replace(" Agent", "")


def load_agent_history():
    if os.path.exists(AGENT_HISTORY_FILE):
        with open(AGENT_HISTORY_FILE) as f:
            return json.load(f)
    return []


def save_agent_history(history):
    with open(AGENT_HISTORY_FILE, "w") as f:
        json.dump(history, f)


if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "restaurant-chat",
        "restaurant-memory.db",
    )
session = st.session_state["session"]

if "agent" not in st.session_state:
    st.session_state["agent"] = triage_agent


async def paint_history():
    messages = await session.get_items()
    agent_history = load_agent_history()
    ai_index = 0
    for message in messages:
        if "role" not in message:
            continue
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        elif message["type"] == "message":
            name = agent_history[ai_index] if ai_index < len(agent_history) else "AI"
            with st.chat_message(name):
                st.write(message["content"][0]["text"])
            ai_index += 1


asyncio.run(paint_history())


async def run_agent(message):
    agents_responded = []
    current_name = agent_display_name(st.session_state["agent"].name)

    msg = None
    text_placeholder = None
    response = ""

    try:
        stream = Runner.run_streamed(
            st.session_state["agent"],
            message,
            session=session,
        )

        async for event in stream.stream_events():
            if event.type == "raw_response_event":
                if event.data.type == "response.output_text.delta":
                    if msg is None:
                        msg = st.chat_message(current_name)
                        text_placeholder = msg.empty()
                    response += event.data.delta
                    text_placeholder.write(response)

            elif event.type == "agent_updated_stream_event":
                if st.session_state["agent"].name != event.new_agent.name:
                    if response:
                        agents_responded.append(current_name)

                    handoff_msg = HANDOFF_MESSAGES.get(event.new_agent.name)
                    if handoff_msg:
                        st.info(handoff_msg)
                    st.session_state["agent"] = event.new_agent
                    current_name = agent_display_name(event.new_agent.name)
                    msg = None
                    text_placeholder = None
                    response = ""

        if response:
            agents_responded.append(current_name)

    except InputGuardrailTripwireTriggered:
        with st.chat_message("Triage"):
            st.write("저는 레스토랑 관련 질문에 대해서만 도와드리고 있어요. 메뉴를 확인하거나, 예약하거나, 음식을 주문할 수 있어요. 😊")

    except OutputGuardrailTripwireTriggered:
        if text_placeholder:
            text_placeholder.empty()
        with st.chat_message(current_name):
            st.write("죄송합니다. 응답을 처리하는 중에 문제가 발생했습니다. 다시 질문해 주세요.")

    history = load_agent_history()
    history.extend(agents_responded)
    save_agent_history(history)


message = st.chat_input("무엇을 도와드릴까요?")

if message:
    with st.chat_message("user"):
        st.write(message)
    asyncio.run(run_agent(message))

with st.sidebar:
    st.subheader("설정")
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
        if os.path.exists(AGENT_HISTORY_FILE):
            os.remove(AGENT_HISTORY_FILE)
        st.session_state["agent"] = triage_agent
        st.rerun()
    st.write(asyncio.run(session.get_items()))
