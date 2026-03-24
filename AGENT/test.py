import requests

BASE_URL = "https://rast-agent-881013919729.us-central1.run.app"
APP_NAME = "src"  # default app name from `adk deploy cloud_run ./src`
USER_ID = "user_123"
SESSION_ID = "session_456"

session_url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
run_url = f"{BASE_URL}/run"

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
            {"text": "What can you do?"}
        ],
    },
}

response = requests.post(run_url, json=payload, timeout=120)
print("run_status:", response.status_code)
print(response.text)
