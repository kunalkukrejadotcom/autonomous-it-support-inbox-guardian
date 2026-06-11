import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.instrumentation import instrument
from agent.root_agent import inbox_guardian

# Auto-initialize instrumentation
instrument()

app = FastAPI(
    title="Autonomous IT Support Inbox Guardian API",
    description="FastAPI backend for Autonomous IT Support Inbox Guardian agent.",
    version="1.0.0"
)

# Enable CORS for Streamlit UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Runner with InMemorySessionService and auto-session creation
session_service = InMemorySessionService()
runner = Runner(
    agent=inbox_guardian,
    app_name="ITSupportGuardian",
    session_service=session_service,
    auto_create_session=True
)

@app.post("/process-inbox")
async def process_inbox(user_id: str = "system_trigger", session_id: str = "default_session"):
    """
    Triggers a cycle of the Inbox Guardian.
    Reads unread emails, triages them, acts, and logs the results.
    """
    events = []
    try:
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text="Process all unread emails in the shared IT support inbox.")]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            events.append(event.model_dump())
        
        return {
            "status": "success",
            "message": "Inbox processing cycle completed.",
            "events": events
        }
    except Exception as e:
        import logging
        logging.error(f"Error during inbox processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred during inbox processing. Please check backend logs for details."
        )

@app.get("/mock-db")
def get_mock_db():
    """
    Retrieves the contents of the mock database files (mock_inbox.json, mock_sheets.json, mock_replies.json).
    Useful for local testing and displaying state in the Streamlit UI.
    """
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_inbox_path = os.path.join(workspace_root, "mock_inbox.json")
    mock_sheets_path = os.path.join(workspace_root, "mock_sheets.json")
    mock_replies_path = os.path.join(workspace_root, "mock_replies.json")

    db_content = {
        "inbox": [],
        "sheets": [],
        "replies": []
    }

    try:
        if os.path.exists(mock_inbox_path):
            with open(mock_inbox_path, "r", encoding="utf-8") as f:
                db_content["inbox"] = json.load(f)
        if os.path.exists(mock_sheets_path):
            with open(mock_sheets_path, "r", encoding="utf-8") as f:
                db_content["sheets"] = json.load(f)
        if os.path.exists(mock_replies_path):
            with open(mock_replies_path, "r", encoding="utf-8") as f:
                db_content["replies"] = json.load(f)
    except Exception as e:
        import logging
        logging.error(f"Failed to read mock database files: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to read mock database files. Please check backend logs for details."
        )

    return db_content

@app.post("/mock-db/reset")
def reset_mock_db():
    """
    Resets the mock database files to their default seeded state.
    """
    try:
        from agent.tools import ensure_mock_files_exist, MOCK_INBOX_PATH, MOCK_SHEETS_PATH, MOCK_REPLIES_PATH
        # Remove the files to force re-seeding
        for path in [MOCK_INBOX_PATH, MOCK_SHEETS_PATH, MOCK_REPLIES_PATH]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        ensure_mock_files_exist()
        return {"status": "success", "message": "Mock database successfully reset."}
    except Exception as e:
        import logging
        logging.error(f"Failed to reset mock database: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to reset mock database. Please check backend logs for details."
        )

if __name__ == "__main__":
    import sys
    if "--cli" in sys.argv:
        async def run_cli():
            print("Starting Autonomous IT Support Inbox Guardian CLI run...")
            user_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text="Process all unread emails in the shared IT support inbox.")]
            )
            try:
                async for event in runner.run_async(
                    user_id="cli_user",
                    session_id="cli_session",
                    new_message=user_message
                ):
                    print(f"Event: {event}")
                print("CLI run completed successfully.")
            except Exception as e:
                print(f"Error during CLI run: {e}")
        asyncio.run(run_cli())
    else:
        import uvicorn
        port = int(os.getenv("PORT", 8000))
        uvicorn.run("agent.main:app", host="0.0.0.0", port=port, reload=True)
