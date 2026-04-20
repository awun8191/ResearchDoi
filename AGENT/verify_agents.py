import asyncio
import os
from typing import Any, AsyncGenerator, List
from dotenv import load_dotenv

# Ensure we are in the right directory for relative imports
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.config import primary_model, init_session_state
from src.agent import root_agent, url_analyst, deep_research_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from google.genai import types

load_dotenv()

async def get_runner(agent):
    session_service = InMemorySessionService()
    await session_service.create_session(app_name="test_app", user_id="test_user", session_id="test_session")
    # Initialize state
    session = await session_service.get_session(app_name="test_app", user_id="test_user", session_id="test_session")
    init_session_state(session.state)
    # Removing update_session as it might not be needed for InMemorySessionService
    
    return Runner(agent=agent, app_name="test_app", session_service=session_service)

async def test_connectivity():
    print("\n--- 1. Connectivity Check ---")
    try:
        agent = LlmAgent(name="test_conn", model=primary_model, instruction="Respond with 'ONLINE'")
        runner = await get_runner(agent)
        
        response_text = ""
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="Hello")])
        ):
            if event.is_final_response():
                response_text = event.content.parts[0].text
                print(f"Response: {response_text.strip()}")
        
        return "ONLINE" in response_text.upper()
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

async def test_orchestration():
    print("\n--- 2. Orchestration Test ---")
    try:
        runner = await get_runner(root_agent)
        found_transfer = False
        
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="Research the latest trends in quantum computing and write a brief outline")])
        ):
            if hasattr(event, "status") and event.status:
                print(f"[STATUS] {event.status}")
            
            if event.status and ("transfer" in event.status.lower() or "handing off" in event.status.lower()):
                found_transfer = True
            
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"[CONTENT] {part.text[:100]}...")
                    if part.call:
                        print(f"[TOOL CALL] {part.call.name}")
                        if "transfer" in part.call.name.lower():
                            found_transfer = True
        
        print(f"Handoff correctly triggered: {found_transfer}")
        return found_transfer
    except Exception as e:
        print(f"Orchestration failed: {e}")
        return False

async def test_url_analyst():
    print("\n--- 3. URL Analyst Verification ---")
    try:
        runner = await get_runner(url_analyst)
        
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="Analyze https://example.com")])
        ):
            if hasattr(event, "status") and event.status:
                print(f"[STATUS] {event.status}")
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"[CONTENT] {part.text[:100]}...")
        return True
    except Exception as e:
        print(f"URL analyst failed: {e}")
        return False

async def test_deep_research():
    print("\n--- 4. Deep Research Verification ---")
    try:
        runner = await get_runner(deep_research_agent)
        count = 0
        async for event in runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(role="user", parts=[types.Part.from_text(text="Quantum computing advancements")])
        ):
            if hasattr(event, "status") and event.status:
                print(f"[STATUS] {event.status}")
            if event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"[CONTENT] {part.text[:100]}...")
            count += 1
            if count > 10: 
                print("Deep research loop started successfully.")
                break
        return True
    except Exception as e:
        print(f"Deep research failed: {e}")
        return False

async def main():
    results = {}
    results["connectivity"] = await test_connectivity()
    results["orchestration"] = await test_orchestration()
    results["url_analyst"] = await test_url_analyst()
    results["deep_research"] = await test_deep_research()
    
    print("\n--- TEST SUMMARY ---")
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{test.upper()}: {status}")

if __name__ == "__main__":
    asyncio.run(main())
