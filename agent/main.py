import os
import json
import asyncio
import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configurable model name via environment, fallback to standard gemini-2.5-flash
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google import genai
from google.genai import types
from pydantic import BaseModel

from agent.instrumentation import instrument
from agent.root_agent import inbox_guardian, create_agent
from agent.tools import is_valid_email
from agent.evaluators import run_trace_evaluations, run_self_improvement

# Auto-initialize instrumentation
instrument()

def sanitize_for_json(data):
    if isinstance(data, dict):
        return {sanitize_for_json(k): sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, bytes):
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="replace")
    elif isinstance(data, (datetime.datetime, datetime.date)):
        return data.isoformat()
    return data

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
async def process_inbox(user_id: str = "system_trigger", session_id: str = "default_session", model_name: str = None):
    """
    Triggers a cycle of the Inbox Guardian.
    Reads unread emails, triages them, acts, and logs the results.
    """
    events = []
    try:
        # Instantiate a fresh Runner using create_agent(model_name)
        agent_instance = create_agent(model_name)
        fresh_runner = Runner(
            agent=agent_instance,
            app_name="ITSupportGuardian",
            session_service=session_service,
            auto_create_session=True
        )
        
        inbox_email = os.getenv("INBOX_EMAIL", "support@example.com")
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Process all unread emails in the shared IT support inbox: {inbox_email}")]
        )
        async for event in fresh_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message
        ):
            events.append(event.model_dump())
        
        safe_events = sanitize_for_json(events)
        return {
            "status": "success",
            "message": "Inbox processing cycle completed.",
            "events": safe_events
        }
    except Exception as e:
        import logging
        logging.error(f"Error during inbox processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
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

class MockEmailRequest(BaseModel):
    from_email: str
    subject: str
    body: str

@app.post("/mock-db/email")
def add_mock_email(req: MockEmailRequest):
    """
    Adds a new mock email to the mock_inbox.json file.
    """
    # 1. Input Validation
    if not req.from_email or not req.from_email.strip():
        raise HTTPException(status_code=400, detail="from_email is required and cannot be empty.")
    if not req.subject or not req.subject.strip():
        raise HTTPException(status_code=400, detail="subject is required and cannot be empty.")
    if not req.body or not req.body.strip():
        raise HTTPException(status_code=400, detail="body is required and cannot be empty.")
        
    if not is_valid_email(req.from_email):
        raise HTTPException(status_code=400, detail="Invalid from_email format.")

    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_inbox_path = os.path.join(workspace_root, "mock_inbox.json")
    
    try:
        inbox = []
        if os.path.exists(mock_inbox_path):
            with open(mock_inbox_path, "r", encoding="utf-8") as f:
                inbox = json.load(f)
        
        # 2. Generate a unique ID (e.g. msg_{timestamp})
        timestamp = int(time.time())
        unique_id = f"msg_{timestamp}"
        
        # Suffix if there's a collision
        existing_ids = {msg.get("id") for msg in inbox}
        counter = 1
        while unique_id in existing_ids:
            unique_id = f"msg_{timestamp}_{counter}"
            counter += 1
            
        snippet = req.body[:80] + "..." if len(req.body) > 80 else req.body
        new_email = {
            "id": unique_id,
            "from_email": req.from_email.strip(),
            "subject": req.subject.strip(),
            "body": req.body,
            "snippet": snippet,
            "is_unread": True,
            "received_at": datetime.datetime.now().isoformat()
        }
        
        inbox.append(new_email)
        with open(mock_inbox_path, "w", encoding="utf-8") as f:
            json.dump(inbox, f, indent=2)
            
        return {"status": "success", "message": "Mock email added successfully.", "email": new_email}
    except HTTPException as he:
        raise he
    except Exception as e:
        import logging
        logging.error(f"Failed to add mock email: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add mock email: {str(e)}"
        )

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

@app.post("/run-evals")
def run_evals(limit: int = 5):
    """
    Triggers run_trace_evaluations(limit) and returns JSON.
    """
    try:
        results = run_trace_evaluations(limit)
        return {"status": "success", "evaluations": results}
    except Exception as e:
        import logging
        logging.error(f"Error running evaluations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running evaluations: {str(e)}"
        )

@app.post("/self-improve")
def self_improve():
    """
    Triggers run_self_improvement() and returns JSON.
    """
    try:
        result = run_self_improvement()
        return result
    except Exception as e:
        import logging
        logging.error(f"Error running self-improvement: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running self-improvement: {str(e)}"
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
