import os
import json
import datetime
import base64
import re
from email.mime.text import MIMEText
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.adk.tools import FunctionTool

# Determine if we run in simulated mode
SIMULATED_MODE = os.getenv("SIMULATED_MODE", "true").lower() == "true"

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

# Resolve mock file paths in the workspace root
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK_INBOX_PATH = os.path.join(WORKSPACE_ROOT, "mock_inbox.json")
MOCK_SHEETS_PATH = os.path.join(WORKSPACE_ROOT, "mock_sheets.json")
MOCK_REPLIES_PATH = os.path.join(WORKSPACE_ROOT, "mock_replies.json")

# Define Google API Scopes
SCOPES = ['https://mail.google.com/', 'https://www.googleapis.com/auth/spreadsheets']

def tool(func):
    """Custom decorator to wrap functions into google-adk FunctionTool."""
    return FunctionTool(func)

def ensure_mock_files_exist():
    """Seeds mock database files if they do not exist in the workspace."""
    # Seed mock_inbox.json with 10 realistic support tickets
    if not os.path.exists(MOCK_INBOX_PATH):
        default_inbox = [
            {
                "id": "msg_001",
                "from_email": "alice.smith@example.com",
                "subject": "Urgent: Password Reset Request",
                "body": "Hi Support, I'm locked out of my corporate login and cannot access my email or Okta. Can you please reset my password? Thanks, Alice.",
                "snippet": "Hi Support, I'm locked out of my corporate login and cannot access my email...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_002",
                "from_email": "bob.jones@example.com",
                "subject": "Printer jam in lobby",
                "body": "The main printer in the lobby is jammed and showing error code 43. We need to print handouts for the client meeting. Can someone help?",
                "snippet": "The main printer in the lobby is jammed and showing error code 43...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_003",
                "from_email": "charlie.brown@example.com",
                "subject": "New Hire Laptop Provisioning - David Lee",
                "body": "Hello IT, we have a new engineer, David Lee, starting next Monday. He needs a standard engineering laptop (MacBook Pro 16\"), external monitor, and access to GitHub, Slack, and AWS. Let me know if you need approval from the VP.",
                "snippet": "Hello IT, we have a new engineer, David Lee, starting next Monday...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_004",
                "from_email": "diana.prince@example.com",
                "subject": "VPN Access Denied",
                "body": "Dear Helpdesk, I am trying to connect to the corporate VPN from home, but it keeps giving me a credential error. I updated my password yesterday. Can you verify if my VPN account is active? Thanks.",
                "snippet": "Dear Helpdesk, I am trying to connect to the corporate VPN from home...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_005",
                "from_email": "evan.wright@example.com",
                "subject": "Salesforce Account Request",
                "body": "Hi, I need access to Salesforce Sales Cloud for the sales lead generation task. My manager is Sarah Jenkins, who approved this request. Please provision my account. Thanks!",
                "snippet": "Hi, I need access to Salesforce Sales Cloud for the sales lead generation task...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_006",
                "from_email": "fiona.gallagher@example.com",
                "subject": "Monitor is flickering",
                "body": "My secondary monitor has started flickering green every few seconds. I've tried unplugging the HDMI cable and plugging it back in, but the issue persists. Is it possible to get a replacement cable or a new monitor? Thanks.",
                "snippet": "My secondary monitor has started flickering green every few seconds...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_007",
                "from_email": "george.costanza@example.com",
                "subject": "Wi-Fi is slow in conference room B",
                "body": "Hi support, the corporate Wi-Fi is barely working in conference room B. We keep dropping off our video calls. Can someone look at the access point in that area?",
                "snippet": "Hi support, the corporate Wi-Fi is barely working in conference room B...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_008",
                "from_email": "harvey.dent@example.com",
                "subject": "Urgent: Phishing email reported",
                "body": "I received an email claiming to be from our CEO asking for my phone number to send gift cards. It looks suspicious. The sender address is ceo-office@gmail.com, not our domain. Please investigate.",
                "snippet": "I received an email claiming to be from our CEO asking for my phone number...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_009",
                "from_email": "irene.adler@example.com",
                "subject": "Zoom login issue",
                "body": "Hi team, I am unable to sign in to Zoom using SSO. It displays an error saying 'User not found in partner directory'. I can log into other Google Workspace apps fine. Please assist.",
                "snippet": "Hi team, I am unable to sign in to Zoom using SSO. It displays an error...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            },
            {
                "id": "msg_010",
                "from_email": "john.watson@example.com",
                "subject": "Software installation: Slack",
                "body": "Hello, I recently got my laptop replaced and need Slack installed. Can you install it for me or send the link to download the corporate version?",
                "snippet": "Hello, I recently got my laptop replaced and need Slack installed...",
                "is_unread": True,
                "received_at": datetime.datetime.now().isoformat()
            }
        ]
        with open(MOCK_INBOX_PATH, "w", encoding="utf-8") as f:
            json.dump(default_inbox, f, indent=2)

    # Seed mock_sheets.json
    if not os.path.exists(MOCK_SHEETS_PATH):
        with open(MOCK_SHEETS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    # Seed mock_replies.json
    if not os.path.exists(MOCK_REPLIES_PATH):
        with open(MOCK_REPLIES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

# Run seeding eagerly
ensure_mock_files_exist()

def get_gmail_service(inbox_email: str):
    """Helper to authenticate and return a Gmail service client with delegation."""
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_path or not os.path.exists(sa_path):
        raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_JSON path '{sa_path}' is invalid or missing.")
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    delegated_creds = creds.with_subject(inbox_email)
    return build('gmail', 'v1', credentials=delegated_creds)

def get_sheets_service():
    """Helper to authenticate and return a Sheets service client."""
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sa_path or not os.path.exists(sa_path):
        raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_JSON path '{sa_path}' is invalid or missing.")
    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    return build('sheets', 'v4', credentials=creds)

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

    if SIMULATED_MODE:
        ensure_mock_files_exist()
        try:
            with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                inbox = json.load(f)
            unread = [msg for msg in inbox if msg.get("is_unread", True)]
            unread = unread[:max_results]
            return json.dumps(unread, indent=2)
        except (json.JSONDecodeError, IOError) as e:
            return f"Error reading mock inbox: {str(e)}"
    else:
        try:
            service = get_gmail_service(inbox_email)
            results = service.users().messages().list(userId='me', q="is:unread", maxResults=max_results).execute()
            messages = results.get('messages', [])
            emails = []
            for msg in messages:
                msg_id = msg['id']
                email_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                
                payload = email_data.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = "No Subject"
                from_email = "Unknown"
                received_at = ""
                
                for h in headers:
                    name = h.get('name', '').lower()
                    if name == 'subject':
                        subject = h.get('value', 'No Subject')
                    elif name == 'from':
                        from_email = h.get('value', 'Unknown')
                    elif name == 'date':
                        received_at = h.get('value', '')
                
                # Extract text body
                body = ""
                parts = [payload]
                while parts:
                    part = parts.pop()
                    if part.get('parts'):
                        parts.extend(part.get('parts'))
                    mime_type = part.get('mimeType', '')
                    if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                        data = part['body']['data']
                        body += base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
                        break
                
                if not body:
                    body = email_data.get('snippet', '')
                    
                emails.append({
                    "id": msg_id,
                    "from_email": from_email,
                    "subject": subject,
                    "body": body,
                    "snippet": email_data.get('snippet', ''),
                    "received_at": received_at,
                    "is_unread": True
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
    if not message_id or not isinstance(message_id, str) or not re.match(r"^[a-zA-Z0-9_@.-]+$", message_id.strip()):
        return "Error: Invalid message_id format."

    if SIMULATED_MODE:
        ensure_mock_files_exist()
        try:
            with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                inbox = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return f"Error reading mock inbox: {str(e)}"
            
        found = False
        original_msg = None
        for msg in inbox:
            if msg.get("id") == message_id:
                msg["is_unread"] = False
                original_msg = msg
                found = True
                break
                
        if not found:
            return f"Error: Email with ID {message_id} not found in mock inbox."
            
        try:
            with open(MOCK_INBOX_PATH, "w", encoding="utf-8") as f:
                json.dump(inbox, f, indent=2)
        except IOError as e:
            return f"Error saving mock inbox: {str(e)}"
            
        # Append to mock_replies.json
        replies = []
        if os.path.exists(MOCK_REPLIES_PATH):
            try:
                with open(MOCK_REPLIES_PATH, "r", encoding="utf-8") as f:
                    replies = json.load(f)
            except Exception:
                replies = []
                
        reply_record = {
            "reply_id": f"rep_{len(replies) + 1:03d}",
            "original_message_id": message_id,
            "to_email": original_msg.get("from_email"),
            "subject": f"Re: {original_msg.get('subject')}",
            "body": body,
            "timestamp": datetime.datetime.now().isoformat()
        }
        replies.append(reply_record)
        
        with open(MOCK_REPLIES_PATH, "w", encoding="utf-8") as f:
            json.dump(replies, f, indent=2)
            
        return f"Reply sent to {original_msg.get('from_email')} and archived original email {message_id}."
    else:
        try:
            service = get_gmail_service(inbox_email)
            original = service.users().messages().get(userId='me', id=message_id, format='metadata', metadataHeaders=['Message-ID', 'Subject', 'From']).execute()
            thread_id = original.get('threadId')
            headers = original.get('payload', {}).get('headers', [])
            
            orig_msg_id = ""
            orig_subject = ""
            orig_from = ""
            for h in headers:
                name = h.get('name', '').lower()
                if name == 'message-id':
                    orig_msg_id = h.get('value', '')
                elif name == 'subject':
                    orig_subject = h.get('value', '')
                elif name == 'from':
                    orig_from = h.get('value', '')
                    
            subject = orig_subject
            if not subject.lower().startswith('re:'):
                subject = 'Re: ' + subject
                
            # Create MIME message
            message = MIMEText(body)
            message['to'] = orig_from
            message['from'] = inbox_email
            message['subject'] = subject
            if orig_msg_id:
                message['In-Reply-To'] = orig_msg_id
                message['References'] = orig_msg_id
                
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            send_body = {
                'raw': raw_message,
                'threadId': thread_id
            }
            
            service.users().messages().send(userId='me', body=send_body).execute()
            
            # Archive (remove UNREAD label)
            service.users().messages().modify(userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}).execute()
            
            return f"Reply sent and archived. Message ID: {message_id}."
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
    if not message_id or not isinstance(message_id, str) or not re.match(r"^[a-zA-Z0-9_@.-]+$", message_id.strip()):
        return "Error: Invalid message_id format."

    if SIMULATED_MODE:
        ensure_mock_files_exist()
        try:
            with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                inbox = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return f"Error reading mock inbox: {str(e)}"

        found = False
        for msg in inbox:
            if msg.get("id") == message_id:
                msg["is_unread"] = False
                found = True
                break

        if not found:
            return f"Error: Email with ID {message_id} not found in mock inbox."

        try:
            with open(MOCK_INBOX_PATH, "w", encoding="utf-8") as f:
                json.dump(inbox, f, indent=2)
        except IOError as e:
            return f"Error saving mock inbox: {str(e)}"

        return f"Email {message_id} successfully archived (marked as read)."
    else:
        try:
            service = get_gmail_service(inbox_email)
            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return f"Email {message_id} successfully archived (UNREAD label removed)."
        except Exception as e:
            return f"Error archiving email: {str(e)}"

@tool
def create_ticket_record(ticket_data: dict = None, **kwargs) -> str:
    """Create a ticket record in the tracking database (mock sheets or live Sheets).
    
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
    reply_body = ticket_data.get("reply_body", "")  # Body can contain newlines, so we don't sanitize it this way
    assigned_owner = sanitize_string(ticket_data.get("assigned_owner", ""))
    status = sanitize_string(ticket_data.get("status", "Open"))
        
    if SIMULATED_MODE:
        ensure_mock_files_exist()
        tickets = []
        if os.path.exists(MOCK_SHEETS_PATH):
            try:
                with open(MOCK_SHEETS_PATH, "r", encoding="utf-8") as f:
                    tickets = json.load(f)
            except Exception:
                tickets = []
                
        ticket_id = ticket_data.get("ticket_id") or f"tkt_{len(tickets) + 1:03d}"
        ticket_id = sanitize_string(ticket_id)
        
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
        tickets.append(record)
        
        with open(MOCK_SHEETS_PATH, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2)
            
        return f"Ticket {ticket_id} successfully logged to mock Sheets."
    else:
        sheet_id = os.getenv("SHEET_ID")
        if not sheet_id:
            return "Error: SHEET_ID is not configured in environment variables."
            
        try:
            service = get_sheets_service()
            range_name = 'Sheet1!A:A'
            try:
                result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_name).execute()
                rows = result.get('values', [])
                num_rows = len(rows)
            except Exception:
                num_rows = 1
                
            ticket_id = ticket_data.get("ticket_id") or f"tkt_{num_rows:03d}"
            ticket_id = sanitize_string(ticket_id)
            timestamp = datetime.datetime.now().isoformat()
            
            values = [[
                ticket_id,
                timestamp,
                sender,
                subject,
                category,
                priority,
                action_taken,
                reply_body,
                assigned_owner,
                status
            ]]
            
            body = {'values': values}
            
            service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range="Sheet1!A:J",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
            return f"Ticket {ticket_id} successfully logged to Google Sheet (id: {sheet_id})."
        except Exception as e:
            return f"Error logging ticket to Google Sheet: {str(e)}"

@tool
def query_phoenix_traces(limit: int = 5) -> str:
    """Retrieve recent traces from Arize Phoenix for self-evaluation and LLM-as-Judge scoring.
    
    Args:
        limit: Number of recent traces to fetch.
        
    Returns:
        A text representation of the recent trace metadata and replies for introspection.
    """
    # Attempt to query live Phoenix server via python client if running, otherwise build mock traces
    traces_str = ""
    try:
        from phoenix.client import Client
        client = Client()
        spans_df = client.get_spans()
        # Find LLM generation spans or tool output spans
        if not spans_df.empty:
            # We can format the DataFrame rows into a text summary
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

    # Simulated/Fallback: query from mock files
    ensure_mock_files_exist()
    if os.path.exists(MOCK_REPLIES_PATH):
        try:
            with open(MOCK_REPLIES_PATH, "r", encoding="utf-8") as f:
                replies = json.load(f)
            with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                inbox = json.load(f)
                
            inbox_map = {msg["id"]: msg for msg in inbox}
            recent_replies = replies[-limit:]
            
            traces_str += f"Found {len(recent_replies)} simulated/mock traces in logs:\n\n"
            for rep in recent_replies:
                orig_id = rep.get("original_message_id")
                orig_msg = inbox_map.get(orig_id, {})
                
                traces_str += f"Trace ID: trace_{rep.get('reply_id')}\n"
                traces_str += f"Timestamp: {rep.get('timestamp')}\n"
                traces_str += f"Sender: {rep.get('to_email')}\n"
                traces_str += f"Subject: {orig_msg.get('subject', 'No Subject')}\n"
                traces_str += f"Customer Query: {orig_msg.get('body', 'No Body')}\n"
                traces_str += f"Agent Reply: {rep.get('body')}\n"
                traces_str += "---\n"
            return traces_str
        except Exception as e:
            return f"Error reading mock logs for traces: {str(e)}"
            
    return "No traces found."
