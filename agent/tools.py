import os
import json
import datetime
import re
from google.cloud import firestore
from google.adk.tools import FunctionTool

def is_valid_email(email: str) -> bool:
    """Validates email format to prevent header injection or invalid queries."""
    if not email or not isinstance(email, str):
        return False
    # Standard email pattern check
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))

def sanitize_string(val: str) -> str:
    """Removes newline and carriage return characters from a string to prevent injection."""
    if not isinstance(val, str):
        return str(val) if val is not None else ""
    return val.replace("\r", "").replace("\n", "").strip()

def tool(func):
    """Custom decorator to wrap functions into google-adk FunctionTool."""
    return FunctionTool(func)

def get_firestore_client() -> firestore.Client:
    """Returns a GCP Firestore Client instance."""
    return firestore.Client()

@tool
def read_unread_emails(inbox_email: str, max_results: int = 20) -> str:
    """Read unread emails in the shared IT support inbox.
    
    Args:
        inbox_email: The target email address (e.g. support@example.com).
        max_results: Maximum number of unread emails to retrieve (default: 20).
        
    Returns:
        A JSON string listing unread emails, each having 'id', 'from_email', 'subject', 'body', 'snippet', and 'received_at'.
    """
    if not is_valid_email(inbox_email):
        return "Error: Invalid inbox_email format."

    try:
        db = get_firestore_client()
        docs = db.collection("inbox").where("is_unread", "==", True).limit(max_results).stream()
        emails = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            emails.append({
                "id": data.get("id"),
                "from_email": data.get("from_email", "Unknown"),
                "subject": data.get("subject", "No Subject"),
                "body": data.get("body", ""),
                "snippet": data.get("snippet", ""),
                "received_at": data.get("received_at", ""),
                "is_unread": data.get("is_unread", True)
            })
        return json.dumps(emails, indent=2)
    except Exception as e:
        return f"Error reading emails: {str(e)}"

@tool
def send_reply(message_id: str, inbox_email: str, body: str) -> str:
    """Send an email reply to a customer/sender and archive/mark read the original email.
    
    Args:
        message_id: The ID of the original email being replied to.
        inbox_email: The target inbox address (e.g. support@example.com).
        body: The content of the reply message.
        
    Returns:
        Status message confirming the reply has been sent and archived.
    """
    if not is_valid_email(inbox_email):
        return "Error: Invalid inbox_email format."
    if not message_id or not isinstance(message_id, str):
        return "Error: Invalid message_id format."

    try:
        db = get_firestore_client()
        doc_ref = db.collection("inbox").document(message_id)
        doc = doc_ref.get()
        if not doc.exists:
            return f"Error: Email with ID {message_id} not found in Firestore."
            
        original_msg = doc.to_dict()
        doc_ref.update({"is_unread": False})
        
        reply_data = {
            "original_message_id": message_id,
            "to_email": original_msg.get("from_email"),
            "subject": f"Re: {original_msg.get('subject', 'No Subject')}",
            "body": body,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        new_doc_ref = db.collection("replies").document()
        reply_data["reply_id"] = new_doc_ref.id
        new_doc_ref.set(reply_data)
        
        return f"Reply sent to {original_msg.get('from_email')} and archived original email {message_id}."
    except Exception as e:
        return f"Error sending reply: {str(e)}"

@tool
def archive_email(message_id: str, inbox_email: str) -> str:
    """Mark an email as read/archived so it is not re-processed in future inbox scans.
    
    This MUST be called for every email that is escalated (Complex Path) since
    `send_reply` is not invoked for those emails and they would otherwise remain
    unread and be picked up again in subsequent processing cycles.
    
    Args:
        message_id: The ID of the email to archive/mark as read.
        inbox_email: The target inbox address (e.g. support@example.com).
        
    Returns:
        Status message confirming the email has been archived.
    """
    if not is_valid_email(inbox_email):
        return "Error: Invalid inbox_email format."
    if not message_id or not isinstance(message_id, str):
        return "Error: Invalid message_id format."

    try:
        db = get_firestore_client()
        doc_ref = db.collection("inbox").document(message_id)
        if not doc_ref.get().exists:
            return f"Error: Email with ID {message_id} not found in Firestore."
        doc_ref.update({"is_unread": False})
        return f"Email {message_id} successfully archived (marked as read)."
    except Exception as e:
        return f"Error archiving email: {str(e)}"

@tool
def create_ticket_record(ticket_data: dict = None, **kwargs) -> str:
    """Create a ticket record in the tracking database (Firestore).
    
    Args:
        ticket_data: A dictionary containing ticket details:
            - 'ticket_id' (optional, generated if not provided)
            - 'sender': Email address of the requester.
            - 'subject': Ticket subject.
            - 'category': Categorization (e.g. Password, Hardware, Software, etc.)
            - 'priority': Priority level (e.g. Low, Medium, High, Urgent)
            - 'action_taken': e.g. 'Auto-Replied' or 'Escalated'
            - 'reply_body': If auto-replied, the body of the reply.
            - 'assigned_owner': If escalated, the assignee owner name.
            - 'status': e.g. 'Resolved' or 'Escalated' or 'Pending'
            
    Returns:
        Status message confirming ticket creation with ID.
    """
    if ticket_data is None:
        ticket_data = kwargs
    else:
        ticket_data = {**ticket_data, **kwargs}
        
    sender = sanitize_string(ticket_data.get("sender", "Unknown"))
    if sender != "Unknown" and not is_valid_email(sender):
        sender = "Invalid Email Address"
        
    subject = sanitize_string(ticket_data.get("subject", "No Subject"))
    category = sanitize_string(ticket_data.get("category", "General"))
    priority = sanitize_string(ticket_data.get("priority", "Medium"))
    action_taken = sanitize_string(ticket_data.get("action_taken", "None"))
    reply_body = ticket_data.get("reply_body", "")
    assigned_owner = sanitize_string(ticket_data.get("assigned_owner", ""))
    status = sanitize_string(ticket_data.get("status", "Open"))

    try:
        db = get_firestore_client()
        ticket_id = ticket_data.get("ticket_id")
        if not ticket_id:
            doc_ref = db.collection("tickets").document()
            ticket_id = doc_ref.id
        else:
            ticket_id = sanitize_string(ticket_id)
            doc_ref = db.collection("tickets").document(ticket_id)
            
        record = {
            "ticket_id": ticket_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "sender": sender,
            "subject": subject,
            "category": category,
            "priority": priority,
            "action_taken": action_taken,
            "reply_body": reply_body,
            "assigned_owner": assigned_owner,
            "status": status
        }
        doc_ref.set(record)
        return f"Ticket {ticket_id} successfully logged to Firestore."
    except Exception as e:
        return f"Error logging ticket to Firestore: {str(e)}"

@tool
def query_phoenix_traces(limit: int = 5) -> str:
    """Retrieve recent traces from Arize Phoenix for self-evaluation and LLM-as-Judge scoring.
    
    Args:
        limit: Number of recent traces to fetch.
        
    Returns:
        A text representation of the recent trace metadata and replies for introspection.
    """
    traces_str = ""
    try:
        from phoenix.client import Client
        client = Client()
        spans_df = client.get_spans()
        if not spans_df.empty:
            recent_spans = spans_df.sort_values(by='start_time', ascending=False).head(limit)
            traces_str += f"Found {len(recent_spans)} live traces in Arize Phoenix:\n"
            for index, row in recent_spans.iterrows():
                traces_str += f"Span ID: {row.get('span_id')}\n"
                traces_str += f"Name: {row.get('name')}\n"
                traces_str += f"Start Time: {row.get('start_time')}\n"
                traces_str += f"Attributes: {row.get('attributes')}\n"
                traces_str += "---\n"
            return traces_str
    except Exception:
        pass

    try:
        db = get_firestore_client()
        replies_ref = db.collection("replies").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        replies = [doc.to_dict() for doc in replies_ref.stream()]
        replies.reverse()
        
        traces_str += f"Found {len(replies)} traces in Firestore:\n\n"
        for rep in replies:
            orig_id = rep.get("original_message_id")
            orig_msg = {}
            if orig_id:
                orig_doc = db.collection("inbox").document(orig_id).get()
                if orig_doc.exists:
                    orig_msg = orig_doc.to_dict()
            
            traces_str += f"Trace ID: trace_{rep.get('reply_id')}\n"
            traces_str += f"Timestamp: {rep.get('timestamp')}\n"
            traces_str += f"Sender: {rep.get('to_email')}\n"
            traces_str += f"Subject: {orig_msg.get('subject', 'No Subject')}\n"
            traces_str += f"Customer Query: {orig_msg.get('body', 'No Body')}\n"
            traces_str += f"Agent Reply: {rep.get('body')}\n"
            traces_str += "---\n"
        return traces_str
    except Exception as e:
        return f"Error reading Firestore for traces: {str(e)}"
