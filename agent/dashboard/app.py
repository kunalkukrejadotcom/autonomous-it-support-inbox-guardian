import streamlit as st
import pandas as pd
import json
import time
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Autonomous IT Support Inbox Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants & Paths
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_PHOENIX_URL = os.getenv("PHOENIX_URL", "http://localhost:6006")
SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "system_prompt.txt")
MOCK_EVALS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "mock_evals.json")

# Helper functions for Backend Integration
def load_evaluations():
    if os.path.exists(MOCK_EVALS_PATH):
        try:
            with open(MOCK_EVALS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.sidebar.error(f"⚠️ Failed to read mock_evals.json: {e}")
    return []

def fetch_db_state(backend_url):
    try:
        response = requests.get(f"{backend_url}/db-state", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.sidebar.error(f"⚠️ FastAPI Backend Offline: {e}")
    return {"inbox": [], "tickets": [], "replies": []}

def load_system_prompt():
    try:
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        st.error(f"Failed to read system prompt: {e}")
    return ""

def save_system_prompt(content):
    try:
        with open(SYSTEM_PROMPT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        st.error(f"Failed to save system prompt: {e}")
    return False

# Sidebar: Configuration & Send Test Email Form & UI Theme Toggle
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 50px;">🛡️</span>
            <h2 style='margin-top: 5px; font-weight: 800;'>INBOX GUARDIAN</h2>
            <p style='color: #64748B; font-size: 13px;'>IT Support Inbox Agentic Triage</p>
        </div>
    """, unsafe_allow_html=True)
    
    # UI Theme Toggle
    theme = st.selectbox("🎨 UI Theme", ["Premium Dark", "Sleek Light"], index=0)
    
    # Gemini Model Dropdown Selector
    selected_model = st.selectbox("🤖 Gemini Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"], index=0)
    
    st.markdown("---")
    st.subheader("⚙️ Backend Configuration")
    backend_url = st.text_input("FastAPI Endpoint URL", value=DEFAULT_BACKEND_URL)
    phoenix_url = st.text_input("Arize Phoenix URL", value=DEFAULT_PHOENIX_URL)
    
    st.markdown("---")
    st.subheader("🖥️ Status Indicators")
    st.markdown("""
        <div style="margin-bottom: 8px;">
            <span class="badge-pill badge-auto" style="font-size: 11px; display: inline-block; width: 100%; text-align: center;">GCP Firestore DB: Active</span>
        </div>
        <div>
            <span class="badge-pill badge-category" style="font-size: 11px; display: inline-block; width: 100%; text-align: center; color: #38BDF8; border-color: rgba(56, 189, 248, 0.3); background-color: rgba(56, 189, 248, 0.15); text-transform: uppercase;">Gmail Interface: Emulated (Firestore Inbox)</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    # Action Trigger Button
    st.subheader("🚀 Manual Action Run")
    run_btn = st.button("Trigger Inbox Triage Now", use_container_width=True, type="primary")
    
    st.markdown("---")
    # Send Test Email Form
    with st.expander("📨 Send Test Email Form", expanded=False):
        with st.form("send_email_form", clear_on_submit=True):
            from_email = st.text_input("From Email", placeholder="user@company.com")
            subject = st.text_input("Subject", placeholder="Need help with...")
            body = st.text_area("Body", placeholder="Explain the issue...")
            submit_email = st.form_submit_button("Send Test Email", use_container_width=True)
            if submit_email:
                if not from_email or not subject or not body:
                    st.error("All fields are required.")
                elif "@" not in from_email:
                    st.error("Invalid email address.")
                else:
                    try:
                        res = requests.post(f"{backend_url}/emails", json={
                            "from_email": from_email,
                            "subject": subject,
                            "body": body
                        })
                        if res.status_code == 200:
                            st.success("Test email sent successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error sending email: {res.text}")
                    except Exception as e:
                         st.error(f"Failed to connect to backend: {e}")

# Fetch database status dynamically
db = fetch_db_state(backend_url)
inbox_list = db.get("inbox", [])
tickets_list = db.get("tickets", db.get("sheets", []))
replies_list = db.get("replies", [])

# Dynamic Theme Colors
if theme == "Premium Dark":
    bg_color = "#0B0F19"
    text_color = "#F8FAFC"
    card_bg = "linear-gradient(135deg, #131E35 0%, #0F172A 100%)"
    card_border = "#1E293B"
    card_text_color = "#FFFFFF"
    log_bg = "#111827"
    log_border = "#1E293B"
    subtitle_color = "#94A3B8"
    code_color_blue = "#38BDF8"
    code_color_pink = "#F472B6"
    code_color_purple = "#A78BFA"
    hr_color = "#1E293B"
else:
    bg_color = "#F8FAFC"
    text_color = "#0F172A"
    card_bg = "linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)"
    card_border = "#BFDBFE"
    card_text_color = "#1E293B"
    log_bg = "#FFFFFF"
    log_border = "#E2E8F0"
    subtitle_color = "#475569"
    code_color_blue = "#0284C7"
    code_color_pink = "#DB2777"
    code_color_purple = "#7C3AED"
    hr_color = "#E2E8F0"

# Inject custom CSS
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {{
        font-family: 'Outfit', sans-serif;
    }}
    
    code, pre, [class*="mono"] {{
        font-family: 'JetBrains Mono', monospace;
    }}
    
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    
    .metrics-container {{
        display: flex;
        gap: 16px;
        margin-bottom: 24px;
        width: 100%;
    }}
    
    .metric-card {{
        flex: 1;
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 24px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .metric-card:hover {{
        transform: translateY(-4px);
        border-color: #3B82F6;
        box-shadow: 0 12px 30px rgba(59, 130, 246, 0.15);
    }}
    
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
    }}
    
    .metric-processed::before {{
        background: linear-gradient(180deg, #6366F1 0%, #4F46E5 100%);
    }}
    
    .metric-resolved::before {{
        background: linear-gradient(180deg, #10B981 0%, #059669 100%);
    }}
    
    .metric-escalated::before {{
        background: linear-gradient(180deg, #F43F5E 0%, #E11D48 100%);
    }}
    
    .metric-title {{
        font-size: 14px;
        color: {subtitle_color};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    
    .metric-value {{
        font-size: 42px;
        font-weight: 800;
        color: {card_text_color};
        margin-top: 8px;
        line-height: 1;
    }}
    
    .metric-subtitle {{
        font-size: 12px;
        color: {subtitle_color};
        margin-top: 8px;
    }}
    
    .status-dot {{
        height: 10px;
        width: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }}
    
    .dot-running {{
        background-color: #3B82F6;
        animation: pulse-running 2s infinite;
    }}
    
    .dot-idle {{
        background-color: #10B981;
        animation: pulse-idle 2s infinite;
    }}
    
    .status-container {{
        display: flex;
        align-items: center;
        padding: 8px 16px;
        background-color: {log_bg};
        border: 1px solid {log_border};
        border-radius: 9999px;
        margin-bottom: 20px;
        width: fit-content;
    }}
    
    .log-row {{
        background-color: {log_bg};
        border: 1px solid {log_border};
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease;
    }}
    
    .log-row:hover {{
        border-color: #3B82F6;
    }}
    
    .badge-pill {{
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .badge-auto {{
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    
    .badge-escalated {{
        background-color: rgba(244, 63, 94, 0.15);
        color: #F43F5E;
        border: 1px solid rgba(244, 63, 94, 0.3);
    }}
    
    .badge-category {{
        background-color: rgba(99, 102, 241, 0.15);
        color: #818CF8;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }}
    
    .gradient-header {{
        background: linear-gradient(90deg, #A855F7 0%, #3B82F6 50%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 4px;
    }}
    
    .sub-title {{
        color: {subtitle_color};
        font-size: 16px;
        margin-bottom: 24px;
    }}
    </style>
""", unsafe_allow_html=True)

# System Status Indicator
is_running = st.session_state.get("is_running", False)
status_label = "Running" if is_running else "Idle"
dot_class = "dot-running" if is_running else "dot-idle"

# Execute Action Run Loop
if run_btn:
    st.session_state.is_running = True
    try:
        with st.status("🔗 Initializing live inbox guardian run...", expanded=True) as status_container:
            st.write("🔍 Scanning shared inbox for new unread emails...")
            st.write(f"📡 Connecting to FastAPI backend at {backend_url}/process-inbox...")
            response = requests.post(f"{backend_url}/process-inbox?model_name={selected_model}", timeout=45)
            if response.status_code == 200:
                result = response.json()
                st.write("✨ Triage cycle completed successfully!")
                status_container.update(label="Triage Loop Completed! All unread emails triaged.", state="complete", expanded=False)
                st.balloons()
                # Trigger a rerun so the database fetches the new state
                st.rerun()
            else:
                try:
                    error_detail = response.json().get("detail")
                except Exception:
                    error_detail = None
                
                if error_detail:
                    st.error(error_detail)
                else:
                    st.error(f"Error calling /process-inbox: {response.status_code} - {response.text}")
                status_container.update(label="Triage Loop Failed", state="error", expanded=True)
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
    finally:
        st.session_state.is_running = False

# Page title / Banner
st.markdown(f"""
    <div>
        <h1 class="gradient-header">Autonomous IT Support Inbox Guardian</h1>
        <p class="sub-title">Google Cloud Rapid Agent Hackathon — Arize Phoenix Observability Track</p>
    </div>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
        <div class="status-container" style="margin-bottom: 0;">
            <span class="status-dot {dot_class}"></span>
            <span style="font-weight: 600; font-size: 14px; color: {text_color}">SYSTEM STATUS: {status_label.upper()}</span>
        </div>
        <div class="status-container" style="margin-bottom: 0; border-color: rgba(16, 185, 129, 0.3);">
            <span class="status-dot" style="background-color: #10B981;"></span>
            <span style="font-weight: 600; font-size: 14px; color: {text_color}">GCP FIRESTORE DB: ACTIVE</span>
        </div>
        <div class="status-container" style="margin-bottom: 0; border-color: rgba(59, 130, 246, 0.3);">
            <span class="status-dot" style="background-color: #3B82F6;"></span>
            <span style="font-weight: 600; font-size: 14px; color: {text_color}">GMAIL INTERFACE: EMULATED (FIRESTORE INBOX)</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Metrics calculation based on actual DB
total_emails = len(inbox_list)
auto_resolved = sum(1 for t in tickets_list if t.get("action_taken") == "Auto-Replied" or t.get("status") == "Resolved")
escalated = sum(1 for t in tickets_list if t.get("action_taken") == "Escalated" or t.get("status") in ["Escalated", "Pending"])

# Row 1: Metrics display cards
st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card metric-processed">
            <div class="metric-title">Total Emails</div>
            <div class="metric-value">{total_emails}</div>
            <div class="metric-subtitle">Total tickets in the mock mailbox</div>
        </div>
        <div class="metric-card metric-resolved">
            <div class="metric-title">Auto-Resolved</div>
            <div class="metric-value">{auto_resolved}</div>
            <div class="metric-subtitle">Routine issues resolved via KB reply</div>
        </div>
        <div class="metric-card metric-escalated">
            <div class="metric-title">Escalated Tickets</div>
            <div class="metric-value">{escalated}</div>
            <div class="metric-subtitle">Complex cases escalated to Sheets/Teams</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Tabs Configuration
tab_log, tab_inbox, tab_phoenix, tab_self_eval = st.tabs([
    "📥 Live Triage Console & Action Log",
    "📬 Mock Inbox Viewer",
    "🔬 Phoenix Observability & Tracing",
    "🧠 Self-Evaluation & Prompt Loop"
])

# ---- TAB 1: Live Triage Console & Action Log ----
with tab_log:
    st.header("Activity Log")
    st.markdown("<p style='color: #64748B; font-size: 14px;'>Displays all ticket logs stored in GCP Firestore DB.</p>", unsafe_allow_html=True)
    
    # Search and Filter tools
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("🔍 Search logs by subject or sender", "", key="log_search")
    with col_filter:
        action_filter = st.selectbox("Filter by Action", ["All", "Auto-Replied", "Escalated"], key="log_filter")
        
    # Build list of logs
    filtered_logs = tickets_list
    if search_query:
        filtered_logs = [l for l in filtered_logs if search_query.lower() in l.get("subject", "").lower() or search_query.lower() in l.get("sender", "").lower()]
    if action_filter != "All":
        filtered_logs = [l for l in filtered_logs if l.get("action_taken", "") == action_filter]
        
    filtered_logs = sorted(filtered_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
        
    if not filtered_logs:
        st.info("No logs found matching criteria.")
    else:
        # Display logs in a premium interactive list
        for l in filtered_logs:
            action = l.get("action_taken", "Unknown")
            badge_action_class = "badge-auto" if action == "Auto-Replied" else "badge-escalated"
            priority = l.get("priority", "Medium")
            status = l.get("status", "Open")
            
            st.markdown(f"""
                <div class="log-row">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span class="badge-pill {badge_action_class}">{action}</span>
                            <span class="badge-pill badge-category" style="margin-left: 8px;">{l.get('category', 'General')}</span>
                            <span style="color: #64748B; font-size: 13px; margin-left: 12px;">{l.get('timestamp', '')}</span>
                        </div>
                        <div>
                            <span style="color: {subtitle_color}; font-size: 13px; font-weight: 600;">Priority: {priority}</span>
                            <span style="color: #10B981; font-size: 13px; font-weight: 600; margin-left: 12px;">Status: {status}</span>
                        </div>
                    </div>
                    <div style="font-size: 16px; font-weight: 700; color: {text_color}; margin-bottom: 4px;">
                        {l.get('subject', 'No Subject')}
                    </div>
                    <div style="color: {subtitle_color}; font-size: 13px; margin-bottom: 8px;">
                        Sender: <code style="color: {code_color_blue};">{l.get('sender', '')}</code> | Ticket ID: <code style="color: {code_color_pink};">{l.get('ticket_id', '')}</code>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"Inspect details for {l.get('ticket_id')}", expanded=False):
                col_r, col_a = st.columns(2)
                with col_r:
                    st.markdown("**🧠 Classification & Priority:**")
                    st.markdown(f"- **Category:** {l.get('category')}")
                    st.markdown(f"- **Priority:** {l.get('priority')}")
                    st.markdown(f"- **Status:** {l.get('status')}")
                    st.markdown(f"- **Assigned Owner:** {l.get('assigned_owner') or 'None (Auto-Resolved)'}")
                with col_a:
                    st.markdown("**🛡️ Action Taken / Reply Body:**")
                    if action == "Auto-Replied":
                        reply_body = l.get("reply_body", "")
                        if not reply_body:
                            matching_reply = next((r for r in replies_list if r.get("original_message_id") == l.get("ticket_id") or r.get("to_email") == l.get("sender")), None)
                            if matching_reply:
                                reply_body = matching_reply.get("body", "")
                        st.code(reply_body or "No reply body saved.", language="text")
                    else:
                        st.code(f"Ticket escalated to {l.get('assigned_owner', 'On-call Support Team')}", language="text")

# ---- TAB 2: Mock Inbox Viewer ----
with tab_inbox:
    st.header("📬 Firestore Mailbox Inbox")
    st.markdown("<p style='color: #64748B; font-size: 14px;'>Displays all messages currently in the Firestore inbox. Unread messages will be processed during the next triage cycle.</p>", unsafe_allow_html=True)
    
    # Button to reset live Firestore DB
    if st.button("🔄 Reset Live Firestore Database to Default", use_container_width=True, key="reset_db_btn"):
        try:
            res = requests.post(f"{backend_url}/db/reset")
            if res.status_code == 200:
                st.success("Firestore database reset successfully!")
                st.rerun()
            else:
                st.error(f"Failed to reset database: {res.text}")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")
            
    st.markdown(f"<hr style='border-color: {hr_color};'/>", unsafe_allow_html=True)
    
    inbox_messages = sorted(inbox_list, key=lambda x: x.get("received_at", ""), reverse=True)
    
    if not inbox_messages:
        st.info("The mailbox is empty.")
    else:
        for msg in inbox_messages:
            is_unread = msg.get("is_unread", True)
            badge_status = "badge-escalated" if is_unread else "badge-auto"
            status_text = "UNREAD" if is_unread else "READ"
            
            st.markdown(f"""
                <div class="log-row">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span class="badge-pill {badge_status}">{status_text}</span>
                            <span style="color: #64748B; font-size: 13px; margin-left: 12px;">{msg.get('received_at', '')}</span>
                        </div>
                        <div style="color: {subtitle_color}; font-size: 13px; font-weight: 600;">
                            ID: <code style="color: {code_color_pink};">{msg.get('id', '')}</code>
                        </div>
                    </div>
                    <div style="font-size: 16px; font-weight: 700; color: {text_color}; margin-bottom: 4px;">
                        {msg.get('subject', 'No Subject')}
                    </div>
                    <div style="color: {subtitle_color}; font-size: 13px; margin-bottom: 8px;">
                        From: <code style="color: {code_color_blue};">{msg.get('from_email', '')}</code>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"View message body for {msg.get('id')}", expanded=False):
                st.text(msg.get("body", ""))

# ---- TAB 3: Phoenix Observability & Tracing ----
with tab_phoenix:
    st.header("Arize Phoenix Integration")
    
    st.markdown(f"""
        <div style="background-color: {log_bg}; border: 1px solid {log_border}; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <h3>🔬 OpenInference Tracing & LLM-as-Judge</h3>
            <p style="color: {subtitle_color};">
                The Autonomous IT Support Inbox Guardian utilizes <b>OpenInference Instrumentation for Google ADK</b> to track agent executions. 
                All tool calls, agent thoughts, planning loops, and API payloads are logged as standardized OpenTelemetry spans and transmitted 
                to our Arize Phoenix collector.
            </p>
            <p style="color: {subtitle_color};">
                From the Arize Phoenix UI, you can perform deep-dive analysis of LLM response latency, token consumption, and execute 
                LLM-as-Judge evaluations to continuously score ticket responses on Helpfulness, Relevance, and Completeness.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    col_info, col_link = st.columns([2, 1])
    
    with col_info:
        st.subheader("📡 Collector Configuration")
        st.markdown(f"""
        * **Project Name**: `it-support-inbox-guardian`
        * **Tracing Endpoint**: `{phoenix_url}/v1/traces`
        * **MCP Status**: `Connected` (Active Settings registered in Gemini CLI)
        * **Otel Instrumentation**: `openinference-instrumentation-google-adk`
        """)
        
    with col_link:
        st.subheader("🌐 Launch Phoenix")
        st.markdown(f"""
            <a href="{phoenix_url}" target="_blank" style="text-decoration: none;">
                <div style="background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%); padding: 20px; border-radius: 12px; text-align: center; color: white; font-weight: 700; box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3); transition: transform 0.2s;">
                    <span style="font-size: 24px; display: block; margin-bottom: 8px;">🚀</span>
                    Open Phoenix Dashboard
                </div>
            </a>
            <div style="text-align: center; margin-top: 10px; font-size: 12px; color: #64748B;">
                URL: {phoenix_url}
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"<hr style='border-color: {hr_color};'/>", unsafe_allow_html=True)
    st.subheader("🖥️ Arize Phoenix Live Dashboard Preview")
    
    iframe_enabled = st.checkbox("Enable Live Iframe Embed", value=False, help="Requires Arize Phoenix local server running on your browser network.")
    if iframe_enabled:
        st.components.v1.iframe(phoenix_url, height=500, scrolling=True)
    else:
        st.markdown(f"""
            <div style="background-color: {log_bg}; border: 1px dashed {log_border}; border-radius: 12px; height: 350px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;">
                <span style="font-size: 40px; margin-bottom: 12px;">📊</span>
                <h4 style="color: {text_color}; margin-bottom: 8px;">Interactive Traces Visualization</h4>
                <p style="color: {subtitle_color}; max-width: 500px; font-size: 13px;">
                    Enable 'Live Iframe Embed' or click 'Open Phoenix Dashboard' to display active trace metrics. 
                    traces include span details, token usage charts, tool run calls, and latency histograms.
                </p>
            </div>
        """, unsafe_allow_html=True)

# ---- TAB 4: Self-Evaluation & Prompt Loop ----
with tab_self_eval:
    st.header("Brain & Memory Self-Improvement Loop")
    
    st.markdown(f"""
        <div style="background-color: {log_bg}; border: 1px solid {log_border}; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <h4>🔄 Prompt Optimization & Judge Feedback Loop</h4>
            <p style="color: {subtitle_color}; font-size: 14px; margin-bottom: 0px;">
                IT Support Guardian runs automated self-evaluation evaluations. By querying recent execution traces via the Phoenix MCP client, 
                the agent evaluates its own performance. If judge metrics drop below target thresholds (e.g. 90%), the agent requests feedback 
                and optimizes its internal triage prompt rule-set dynamically.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. Trigger Button
    if st.button("🚀 Run Trace Evaluations & Self-Improvement Loop", type="primary", use_container_width=True, key="run_eval_loop_btn"):
        try:
            with st.status("🔗 Running automated self-improvement cycle...", expanded=True) as status_container:
                st.write("🔬 Querying recent traces and evaluating via LLM-as-Judge...")
                eval_res = requests.post(f"{backend_url}/run-evals?limit=5", timeout=30)
                if eval_res.status_code == 200:
                    st.write("✨ Evaluation complete! Running self-improvement to optimize prompt rules...")
                    improve_res = requests.post(f"{backend_url}/self-improve", timeout=30)
                    if improve_res.status_code == 200:
                        st.write("🤖 System prompt successfully optimized based on recommendations!")
                        status_container.update(label="Self-Improvement Loop Completed!", state="complete", expanded=False)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"Self-improvement failed: {improve_res.text}")
                        status_container.update(label="Self-Improvement Failed", state="error", expanded=True)
                else:
                    st.error(f"Evaluation failed: {eval_res.text}")
                    status_container.update(label="Evaluation Failed", state="error", expanded=True)
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_chart, col_rules = st.columns([1, 1])
    
    with col_chart:
        st.subheader("📈 LLM-as-Judge Metric Trends")
        
        # Load and parse actual evaluations from mock_evals.json
        evals = load_evaluations()
        
        if not evals:
            st.info("No evaluation data found. Run the self-improvement loop to generate metrics.")
        else:
            records = []
            for idx, ev in enumerate(evals):
                ts_str = ev.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts_str)
                    display_time = dt.strftime("%m-%d %H:%M")
                except Exception:
                    display_time = f"Run {idx + 1}"
                    
                h_val = ev.get("helpfulness")
                if h_val is None:
                    h_score = ev.get("helpfulness_score")
                    h_val = float(h_score) / 5.0 if h_score is not None else 0.0
                    
                c_val = ev.get("completeness")
                if c_val is None:
                    c_score = ev.get("completeness_score")
                    c_val = float(c_score) / 5.0 if c_score is not None else 0.0
                    
                t_val = ev.get("tone")
                if t_val is None:
                    t_score = ev.get("tone_score")
                    t_val = float(t_score) / 5.0 if t_score is not None else 0.0
                    
                records.append({
                    "Time/Run": display_time,
                    "Helpfulness": h_val,
                    "Completeness": c_val,
                    "Tone": t_val
                })
                
            eval_data = pd.DataFrame(records).set_index("Time/Run")
            st.line_chart(eval_data, height=300)
            
            # Display target threshold and metrics
            latest_ev = evals[-1]
            h_latest = latest_ev.get("helpfulness")
            if h_latest is None:
                h_score = latest_ev.get("helpfulness_score")
                h_latest = float(h_score) / 5.0 if h_score is not None else 0.0
                
            c_latest = latest_ev.get("completeness")
            if c_latest is None:
                c_score = latest_ev.get("completeness_score")
                c_latest = float(c_score) / 5.0 if c_score is not None else 0.0
                
            t_latest = latest_ev.get("tone")
            if t_latest is None:
                t_score = latest_ev.get("tone_score")
                t_latest = float(t_score) / 5.0 if t_score is not None else 0.0
                
            st.markdown(f"""
                * **Target Threshold**: `0.90` (Target line)
                * **Evaluation Model**: `{selected_model}` (LLM-as-Judge)
                * **Latest Helpfulness**: `{h_latest*100:.0f}%` | **Completeness**: `{c_latest*100:.0f}%` | **Tone**: `{t_latest*100:.0f}%`
            """)
            
            # Display latest reasoning and recommendations dynamically
            latest_rec = latest_ev.get('improvement_recommendations') or latest_ev.get('recommendation') or 'No recommendation provided.'
            st.markdown(f"""
                <div style="background-color: {log_bg}; border: 1px solid {log_border}; border-radius: 12px; padding: 16px; margin-top: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <h5 style="color: {text_color}; margin-top: 0px; margin-bottom: 8px; font-weight: 700;">🧠 Latest Judge Analysis</h5>
                    <p style="color: {text_color}; font-size: 13.5px; margin-bottom: 8px; line-height: 1.5;">
                        <b>Reasoning:</b> {latest_ev.get('reasoning', 'No reasoning provided.')}
                     </p>
                     <p style="color: {code_color_purple}; font-size: 13.5px; margin-bottom: 0px; font-weight: 600;">
                         💡 <b>Recommendation:</b> {latest_rec}
                     </p>
                </div>
            """, unsafe_allow_html=True)
            
    with col_rules:
        st.subheader("📝 Active Prompt Instructions")
        st.markdown("<p style='color: #64748B; font-size: 12px; margin-top: -10px;'>Modify system instructions dynamically. Updates will optimize subsequent triage runs.</p>", unsafe_allow_html=True)
        
        current_prompt = load_system_prompt()
        prompt_input = st.text_area(
            "Agent Instruction Set (Stored in prompts/system_prompt.txt)",
            value=current_prompt,
            height=300
        )
        
        if st.button("Save & Refine Agent Rules", type="secondary", key="save_rules_btn"):
            if save_system_prompt(prompt_input):
                st.toast("Agent prompt instructions saved to prompts/system_prompt.txt!")
                st.success("Instructions synchronized successfully. system_prompt.txt updated.")
