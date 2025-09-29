# backend/app/tests/unit/test_job_websocket.py

import asyncio
import json
from uuid import uuid4
from datetime import date, timedelta

import httpx
import pytest
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatus

# --- Configuration ---
# Replace with your actual running application's URL
BASE_API_URL = "http://127.0.0.1:8000"
BASE_WS_URL = "ws://127.0.0.1:8000"

# Replace with valid credentials for a user in your database
TEST_USER_EMAIL = "admin@baze.edu.ng"
TEST_USER_PASSWORD = "admin123"

# Replace with a valid session UUID from your database
SESSION_ID = "692d13f5-fbfc-4a21-ac7e-fa909ef6e4d2"


async def get_auth_token(client: httpx.AsyncClient) -> str:
    """Authenticate and retrieve an access token."""
    print("--- 1. Authenticating ---")
    try:
        response = await client.post(
            f"{BASE_API_URL}/api/v1/auth/token",
            data={"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        response.raise_for_status()
        token_data = response.json()
        print(f"Successfully authenticated. Token Type: {token_data['token_type']}")
        return token_data["access_token"]
    except httpx.HTTPStatusError as e:
        print(f"Authentication failed: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        print(f"Could not connect to the authentication endpoint: {e}")
        raise


async def start_timetable_job(client: httpx.AsyncClient, token: str) -> str:
    """Start a new timetable generation job and return its ID."""
    print("\n--- 2. Starting Timetable Generation Job ---")
    headers = {"Authorization": f"Bearer {token}"}
    start_date = date.today()
    end_date = start_date + timedelta(days=30)

    payload = {
        "session_id": SESSION_ID,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "options": {"solver_time_limit_seconds": 10},
    }
    try:
        response = await client.post(
            f"{BASE_API_URL}/api/v1/scheduling/generate",
            headers=headers,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"Job started successfully. Job ID: {job_id}")
        return job_id
    except httpx.HTTPStatusError as e:
        print(f"Failed to start job: {e.response.status_code} - {e.response.text}")
        raise
    except httpx.RequestError as e:
        print(f"Could not connect to the job generation endpoint: {e}")
        raise


@pytest.mark.asyncio
async def test_timetable_job_websocket_updates():
    """
    Full test workflow:
    1. Authenticates to get a token.
    2. Starts a timetable generation job.
    3. Connects to the WebSocket for that job.
    4. Listens for messages until a final "completed" or "failed" status is received.
    """
    async with httpx.AsyncClient() as client:
        try:
            token = await get_auth_token(client)
            job_id = await start_timetable_job(client, token)
        except (httpx.RequestError, httpx.HTTPStatusError):
            pytest.fail("Prerequisites for WebSocket test failed (API calls).")
            return

        ws_url = f"{BASE_WS_URL}/api/v1/ws/jobs/{job_id}"
        headers = {"Authorization": f"Bearer {token}"}

        print(f"\n--- 3. Connecting to WebSocket: {ws_url} ---")

        try:
            async with websockets.connect(
                ws_url, additional_headers=headers
            ) as websocket:
                print("WebSocket connection successful. Waiting for messages...")

                final_status_received = None

                # Listen for messages in a loop
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=45)
                        data = json.loads(message)

                        status = data.get("status", "unknown")
                        progress = data.get("progress", 0)
                        phase = data.get("phase", "N/A")

                        print(
                            f"  [RECV] Status: {status}, Progress: {progress}%, Phase: {phase}"
                        )

                        if status in ["completed", "failed"]:
                            final_status_received = status
                            if status == "completed":
                                assert (
                                    "result" in data
                                ), "Completed message should contain results"
                            break

                    except asyncio.TimeoutError:
                        pytest.fail("WebSocket timed out waiting for a final message.")
                        break

                # Assert that we received a valid final status
                assert (
                    final_status_received == "completed"
                ), f"Job ended with status '{final_status_received}' instead of 'completed'"
                print(
                    f"\n--- 4. Test PASSED: Received final status '{final_status_received}' ---"
                )

                # The server should close the connection after the final message
                with pytest.raises(ConnectionClosed):
                    await asyncio.wait_for(websocket.recv(), timeout=2)
                print("Server correctly closed the connection after job completion.")

        except (InvalidStatus, ConnectionClosed, Exception) as e:
            pytest.fail(f"WebSocket connection or communication failed: {e}")
