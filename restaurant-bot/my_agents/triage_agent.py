from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters
from my_agents.menu_agent import menu_agent
from my_agents.order_agent import order_agent
from my_agents.reservation_agent import reservation_agent

triage_agent = Agent(
    name="Triage Agent",
    instructions=f"""
    {RECOMMENDED_PROMPT_PREFIX}

    You are the first point of contact at our restaurant. Greet customers warmly and figure out what they need.

    Route to the right specialist based on the request:
    - Menu Agent: questions about menu items, ingredients, allergens, dietary options (vegetarian, vegan, gluten-free)
    - Order Agent: placing or modifying an order
    - Reservation Agent: making, changing, or cancelling a table reservation

    Before handing off, briefly tell the customer who you're connecting them with.
    Example: "예약 담당자에게 연결해 드릴게요!" or "메뉴 전문가에게 바로 연결해 드릴게요!"

    If the request is unclear, ask one short clarifying question.
    Respond in Korean if the customer writes in Korean.
    """,
    handoffs=[
        handoff(agent=menu_agent, input_filter=handoff_filters.remove_all_tools),
        handoff(agent=order_agent, input_filter=handoff_filters.remove_all_tools),
        handoff(agent=reservation_agent, input_filter=handoff_filters.remove_all_tools),
    ],
)
