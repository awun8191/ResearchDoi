import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"
APP_NAME = "src"  
USER_ID = "user_123"
SESSION_ID = f"session_{int(time.time())}"

session_url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
run_url = f"{BASE_URL}/run"

print(f"Creating session at {session_url}...")
session_response = requests.post(session_url, timeout=30)
print("create_session_status:", session_response.status_code)
if session_response.status_code not in (200, 409):
    print(session_response.text)
    raise SystemExit(1)

payload = {
    "app_name": APP_NAME,
    "user_id": USER_ID,
    "session_id": SESSION_ID,
    "new_message": {
        "role": "user",
        "parts": [
            {"text": "Research and write an outline on quantum computing"}
        ],
    },
}

print(f"Sending request to {run_url}...")
# Use stream=True to handle long-running agent tasks and SSE
response = requests.post(run_url, json=payload, timeout=300, stream=True)
print("run_status:", response.status_code)

if response.status_code == 200:
    try:
        # Iterate over the response stream
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    try:
                        event_data = json.loads(decoded_line[6:])
                        if 'content' in event_data:
                            author = event_data.get('author', 'Assistant')
                            text = ""
                            if 'parts' in event_data['content']:
                                for part in event_data['content']['parts']:
                                    if 'text' in part:
                                        text += part['text']
                            if text:
                                print(f"[{author}]: {text}")
                        elif 'status' in event_data:
                             print(f"Status: {event_data['status']}")
                        # Handle termination events if any
                        if event_data.get('type') == 'done':
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error parsing stream: {e}")
else:
    print(response.text)
