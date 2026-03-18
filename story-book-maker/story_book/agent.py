import base64
from openai import OpenAI
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from .prompt import (
    STORY_WRITER_DESCRIPTION,
    ILLUSTRATOR_DESCRIPTION,
    STORY_WRITER_INSTRUCTION,
    ILLUSTRATOR_INSTRUCTION,
)

MODEL = LiteLlm(model="openai/gpt-4o")

story_writer_agent = Agent(
    name="StoryWriterAgent",
    description=STORY_WRITER_DESCRIPTION,
    instruction=STORY_WRITER_INSTRUCTION,
    output_key="story_pages",
    model=MODEL,
)


async def generate_page_image(
    page_number: int,
    visual_description: str,
    character_description: str,
    art_style: str,
    tool_context: ToolContext,
):
    """Generate an illustration for a story page and save it as an artifact.

    Args:
        page_number: The page number (1-5).
        visual_description: A description of the scene to illustrate.
        character_description: Consistent physical description of the main character.
        art_style: Consistent art style to apply across all pages.
    """
    prompt = (
        f"{art_style}. "
        f"Main character: {character_description}. "
        f"Scene: {visual_description}"
    )
    client = OpenAI()
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        response_format="b64_json",
    )
    image_data = base64.b64decode(response.data[0].b64_json)
    filename = f"page_{page_number}.png"
    await tool_context.save_artifact(
        filename=filename,
        artifact=types.Part.from_bytes(data=image_data, mime_type="image/png"),
    )
    return f"Image for page {page_number} saved as artifact: {filename}"


illustrator_agent = Agent(
    name="IllustratorAgent",
    description=ILLUSTRATOR_DESCRIPTION,
    instruction=ILLUSTRATOR_INSTRUCTION,
    tools=[generate_page_image],
    model=MODEL,
)

root_agent = SequentialAgent(
    name="StoryBookMaker",
    description="A pipeline that writes a children's story and generates an illustration for each page.",
    sub_agents=[story_writer_agent, illustrator_agent],
)
