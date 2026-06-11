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

from agent.instrumentation import instrument, get_status as get_tracing_status
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

@app.get("/health/tracing")
def health_tracing():
    """
    Diagnostic endpoint: returns current Phoenix tracing status.
    Checks whether PHOENIX_COLLECTOR_ENDPOINT is set and the tracer provider initialized.
    """
    import requests as _requests
    status = get_tracing_status()
    endpoint = status["endpoint"]

    # Derive the Phoenix base URL by stripping /v1/traces
    phoenix_base = endpoint.replace("/v1/traces", "").rstrip("/") if endpoint != "NOT SET" else ""

    # Connectivity check: GET the Phoenix root — much more reliable than POSTing OTLP
    phoenix_reachable = False
    phoenix_status_code = None
    phoenix_error = None
    if phoenix_base:
        try:
            resp = _requests.get(phoenix_base, timeout=5)
            phoenix_status_code = resp.status_code
            phoenix_reachable = resp.status_code < 500
        except Exception as e:
            phoenix_error = str(e)

    return {
        **status,
        "phoenix_base_url": phoenix_base or "NOT SET",
        "phoenix_ui_reachable": phoenix_reachable,
        "phoenix_ui_status_code": phoenix_status_code,
        "phoenix_ui_error": phoenix_error,
    }

@app.post("/test-tracing")
def test_tracing():
    """
    Diagnostic endpoint: manually emits a test span via the configured tracer provider.
    If tracing is not initialized, returns an error with the reason.
    """
    from agent.instrumentation import _tracer_provider
    status = get_tracing_status()

    if not _tracer_provider:
        return {
            "status": "tracing_not_initialized",
            "reason": "_tracer_provider is None — check PHOENIX_COLLECTOR_ENDPOINT env var and Cloud Run logs",
            "tracing_status": status,
        }

    try:
        tracer = _tracer_provider.get_tracer("inbox-guardian-test")
        with tracer.start_as_current_span("manual-test-span") as span:
            span.set_attribute("test.source", "test-tracing-endpoint")
            span.set_attribute("test.manual", True)
        # Force flush so span is exported immediately
        _tracer_provider.force_flush(timeout_millis=5000)
        return {
            "status": "span_emitted",
            "message": "Test span 'manual-test-span' sent to Phoenix. Check your Phoenix dashboard.",
            "endpoint": status["endpoint"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

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

class EmailRequest(BaseModel):
    from_email: str
    subject: str
    body: str

@app.get("/db-state")
def get_db_state():
    """
    Retrieves the contents of the Firestore collections (inbox, replies, tickets).
    """
    try:
        from agent.tools import get_firestore_client
        db = get_firestore_client()
        
        inbox_docs = db.collection("inbox").stream()
        tickets_docs = db.collection("tickets").stream()
        replies_docs = db.collection("replies").stream()
        
        inbox = []
        for doc in inbox_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            inbox.append(data)
            
        tickets = []
        for doc in tickets_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            tickets.append(data)
            
        replies = []
        for doc in replies_docs:
            data = doc.to_dict()
            data["id"] = doc.id
            replies.append(data)
            
        return {
            "inbox": inbox,
            "tickets": tickets,
            "replies": replies
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to read Firestore database state: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read Firestore state: {str(e)}"
        )

@app.post("/emails")
def add_email(req: EmailRequest):
    """
    Adds a new unread email to the Firestore inbox collection.
    """
    if not req.from_email or not req.from_email.strip():
        raise HTTPException(status_code=400, detail="from_email is required and cannot be empty.")
    if not req.subject or not req.subject.strip():
        raise HTTPException(status_code=400, detail="subject is required and cannot be empty.")
    if not req.body or not req.body.strip():
        raise HTTPException(status_code=400, detail="body is required and cannot be empty.")
        
    if not is_valid_email(req.from_email):
        raise HTTPException(status_code=400, detail="Invalid from_email format.")

    try:
        from agent.tools import get_firestore_client
        db = get_firestore_client()
        
        timestamp = int(time.time())
        unique_id = f"msg_{timestamp}"
        
        doc_ref = db.collection("inbox").document(unique_id)
        counter = 1
        while doc_ref.get().exists:
            unique_id = f"msg_{timestamp}_{counter}"
            doc_ref = db.collection("inbox").document(unique_id)
            counter += 1
            
        snippet = req.body[:80] + "..." if len(req.body) > 80 else req.body
        new_email = {
            "from_email": req.from_email.strip(),
            "subject": req.subject.strip(),
            "body": req.body,
            "snippet": snippet,
            "is_unread": True,
            "received_at": datetime.datetime.now().isoformat()
        }
        
        doc_ref.set(new_email)
        new_email["id"] = unique_id
        
        return {"status": "success", "message": "Email added successfully.", "email": new_email}
    except HTTPException as he:
        raise he
    except Exception as e:
        import logging
        logging.error(f"Failed to add email: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add email: {str(e)}"
        )

@app.post("/db/reset")
def reset_db():
    """
    Purges Firestore collections (inbox, replies, tickets) and seeds the default 10 test emails to inbox.
    """
    try:
        from agent.tools import get_firestore_client
        db = get_firestore_client()
        
        # Purge collections
        for collection_name in ["inbox", "replies", "tickets"]:
            docs = db.collection(collection_name).stream()
            for doc in docs:
                doc.reference.delete()
                
        # Seed 10 test emails
        default_inbox = [
            {
                "id": "msg_001",
                "from_email": "alice.smith@example.com",
                "subject": "Urgent: Password Reset Request",
                "body": "Hi Support, I'm locked out of my corporate login and cannot access my email or Okta. Can you please reset my password? Thanks, Alice.",
                "snippet": "Hi Support, I'm locked out of my corporate login and cannot access my email...",
                "is_unread": True
            },
            {
                "id": "msg_002",
                "from_email": "bob.jones@example.com",
                "subject": "Printer jam in lobby",
                "body": "The main printer in the lobby is jammed and showing error code 43. We need to print handouts for the client meeting. Can someone help?",
                "snippet": "The main printer in the lobby is jammed and showing error code 43...",
                "is_unread": True
            },
            {
                "id": "msg_003",
                "from_email": "charlie.brown@example.com",
                "subject": "New Hire Laptop Provisioning - David Lee",
                "body": "Hello IT, we have a new engineer, David Lee, starting next Monday. He needs a standard engineering laptop (MacBook Pro 16\"), external monitor, and access to GitHub, Slack, and AWS. Let me know if you need approval from the VP.",
                "snippet": "Hello IT, we have a new engineer, David Lee, starting next Monday...",
                "is_unread": True
            },
            {
                "id": "msg_004",
                "from_email": "diana.prince@example.com",
                "subject": "VPN Access Denied",
                "body": "Dear Helpdesk, I am trying to connect to the corporate VPN from home, but it keeps giving me a credential error. I updated my password yesterday. Can you verify if my VPN account is active? Thanks.",
                "snippet": "Dear Helpdesk, I am trying to connect to the corporate VPN from home...",
                "is_unread": True
            },
            {
                "id": "msg_005",
                "from_email": "evan.wright@example.com",
                "subject": "Salesforce Account Request",
                "body": "Hi, I need access to Salesforce Sales Cloud for the sales lead generation task. My manager is Sarah Jenkins, who approved this request. Please provision my account. Thanks!",
                "snippet": "Hi, I need access to Salesforce Sales Cloud for the sales lead generation task...",
                "is_unread": True
            },
            {
                "id": "msg_006",
                "from_email": "fiona.gallagher@example.com",
                "subject": "Monitor is flickering",
                "body": "My secondary monitor has started flickering green every few seconds. I've tried unplugging the HDMI cable and plugging it back in, but the issue persists. Is it possible to get a replacement cable or a new monitor? Thanks.",
                "snippet": "My secondary monitor has started flickering green every few seconds...",
                "is_unread": True
            },
            {
                "id": "msg_007",
                "from_email": "george.costanza@example.com",
                "subject": "Wi-Fi is slow in conference room B",
                "body": "Hi support, the corporate Wi-Fi is barely working in conference room B. We keep dropping off our video calls. Can someone look at the access point in that area?",
                "snippet": "Hi support, the corporate Wi-Fi is barely working in conference room B...",
                "is_unread": True
            },
            {
                "id": "msg_008",
                "from_email": "harvey.dent@example.com",
                "subject": "Urgent: Phishing email reported",
                "body": "I received an email claiming to be from our CEO asking for my phone number to send gift cards. It looks suspicious. The sender address is ceo-office@gmail.com, not our domain. Please investigate.",
                "snippet": "I received an email claiming to be from our CEO asking for my phone number...",
                "is_unread": True
            },
            {
                "id": "msg_009",
                "from_email": "irene.adler@example.com",
                "subject": "Zoom login issue",
                "body": "Hi team, I am unable to sign in to Zoom using SSO. It displays an error saying 'User not found in partner directory'. I can log into other Google Workspace apps fine. Please assist.",
                "snippet": "Hi team, I am unable to sign in to Zoom using SSO. It displays an error...",
                "is_unread": True
            },
            {
                "id": "msg_010",
                "from_email": "john.watson@example.com",
                "subject": "Software installation: Slack",
                "body": "Hello, I recently got my laptop replaced and need Slack installed. Can you install it for me or send the link to download the corporate version?",
                "snippet": "Hello, I recently got my laptop replaced and need Slack installed...",
                "is_unread": True
            }
        ]
        
        for msg in default_inbox:
            doc_id = msg.pop("id")
            msg["received_at"] = datetime.datetime.now().isoformat()
            db.collection("inbox").document(doc_id).set(msg)
            
        return {"status": "success", "message": "Firestore database successfully reset and seeded."}
    except Exception as e:
        import logging
        logging.error(f"Failed to reset Firestore: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset Firestore: {str(e)}"
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
