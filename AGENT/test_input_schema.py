
import asyncio
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from src.config import primary_model

class TestSchema(BaseModel):
    topic: str = Field(..., description="The topic")

agent = LlmAgent(
    name="TestAgent",
    model=primary_model,
    input_schema=TestSchema,
    instruction="Tell me about {topic}"
)

async def main():
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="test", user_id="u", session_id="s")
    runner = Runner(agent=agent, app_name="test", session_service=session_service)
    
    print("Testing with dict input...")
    try:
        async for event in runner.run_async(
            user_id="u",
            session_id="s",
            input_data={"topic": "Quantum Computing"}
        ):
            if event.content:
                print(f"Response: {event.content.parts[0].text[:50]}...")
    except Exception as e:
        print(f"Dict input failed: {e}")

    print("\nTesting with text input...")
    try:
        async for event in runner.run_async(
            user_id="u",
            session_id="s",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="Quantum Computing")])
        ):
            if event.content:
                print(f"Response: {event.content.parts[0].text[:50]}...")
    except Exception as e:
        print(f"Text input failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
