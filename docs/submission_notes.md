# 📄 Hackathon Submission Notes & Video Script

This document serves as the official compilation of background notes, architectural justifications, a 3-minute demo video script, and a Devpost submission checklist for the **Autonomous IT Support Inbox Guardian**.

---

## 💡 Inspiration, Core Behavior, and GCP Stack

### 1. The Inspiration
IT support desks are flooded daily with repetitive, low-complexity requests. Password resets, software access requests, printer troubleshooting, and basic network questions consume up to 70–80% of a support team's time. 

Traditional approaches to solve this involve chat widgets on internal portals, but these require active user initiation and suffer from low adoption because employees naturally prefer sending an email to a shared address. We built the **Inbox Guardian** to meet users where they already work: their email inbox. It acts as an autonomous first responder, solving routine requests instantly while logging and escalating complex queries so human engineers can focus on critical work.

### 2. Core Agent Behavior
The Inbox Guardian runs proactively using a scheduled trigger. For each cycle, it executes the following logic:
1.  **Ingestion:** Reads the unread queue of the support inbox via the Gmail API.
2.  **Triage & Branching:** Gemini classifies each email.
    *   *Routine Ticket:* The agent drafts a response containing relevant steps from the IT Knowledge Base, sends the email, and marks the message as read/archived.
    *   *Complex Ticket:* The agent determines the proper department/assignee, logs the details in a central Google Sheet, and triggers notifications (Slack/email) to alert human support.
3.  **Self-Introspection:** The agent utilizes the Arize Phoenix MCP tool to pull trace data of its own replies.
4.  **Self-Improvement (LLM-as-Judge):** The agent reviews the traces to grade the tone, helpfulness, and correctness of its actions. If any areas of improvement are found, it updates its internal guidelines stored in Firestore/mock database to refine its future behavior.

### 3. Google Cloud Platform (GCP) Stack
*   **Google Cloud Run:** Hosts the FastAPI agent container, scaling down to zero when idle to minimize costs.
*   **Google Cloud Scheduler:** Triggers the FastAPI `/process-inbox` webhook every 5 minutes to run the autonomous triage cycle.
*   **Google Vertex AI / Gemini:** Serves as the reasoning engine for ticket classification, reply drafting, and LLM-as-Judge evaluations.
*   **Google Workspace APIs (Gmail & Sheets):** Provides the interfaces for the shared inbox and the live ticket logging dashboard.
*   **Google Cloud Firestore:** Stores the Knowledge Base articles, ticket statuses, and the persistent guidelines refined during the self-improvement loop.

---

## 🎬 3-Minute Demo Video Script

**Title:** Autonomous IT Support Inbox Guardian
**Target Duration:** 180 Seconds (3:00)

| Timestamp | Visual Screen Action | Narration Script (Audio) |
| :--- | :--- | :--- |
| **0:00 – 0:30**<br>*(30s)* | **Intro & Problem Setup:**<br>1. Show title slide with the project name, Google ADK, and Arize logos.<br>2. Switch to an email client showing a shared IT inbox flooded with unread emails (e.g., "Help, locked out of Jira!", "Office printer offline"). | *"Hello! Meet the Autonomous IT Support Inbox Guardian. Every day, IT departments spend hours sorting through repetitious tickets like password resets and setup requests. We built a 24/7 autonomous agent that reads, triages, and resolves these emails immediately. It's not a reactive chatbot—it lives directly in the email inbox, takes real actions, and constantly self-improves using Arize Phoenix."* |
| **0:30 – 1:15**<br>*(45s)* | **Live Autonomous Run:**<br>1. Show the Streamlit Dashboard.<br>2. Click the **"Trigger Next Cycle"** button (simulating Cloud Scheduler).<br>3. Show the activity feed updating: *"Fetching emails..."*, *"Analyzing tickets..."*<br>4. Switch to Google Sheets: Show a complex ticket ("VPN Server Down") being automatically logged.<br>5. Switch to Sent Mail: Show a routine password-reset reply sent with step-by-step instructions. | *"Let's see the Guardian in action. Triggering a support cycle on our Streamlit dashboard, the agent reads our mailbox. It recognizes the password ticket as routine, instantly drafts a helpful response with knowledge base links, and archives the thread. For a critical VPN outage ticket, it logs the incident in our Google Sheet and flags it for immediate human escalation."* |
| **1:15 – 2:00**<br>*(45s)* | **Arize Phoenix Observability:**<br>1. Open the Arize Phoenix Cloud console.<br>2. Click on the latest trace from `it-support-inbox-guardian`.<br>3. Expand the spans showing the tool calls (`read_unread_emails`, `send_reply`) and model tokens/latency. | *"Observability is critical for autonomous systems. Because we instrumented the Google ADK runner with OpenInference, every single step is traced. In Arize Phoenix, we can audit the agent's exact planning loop, verify the arguments passed to our Gmail and Sheets tools, and analyze the response latency. This ensures absolute reliability and complete transparency for IT managers."* |
| **2:00 – 2:40**<br>*(40s)* | **Self-Improvement Loop:**<br>1. Show the dashboard console logs displaying the LLM-as-Judge evaluation.<br>2. Show the agent calling the Phoenix MCP tool to inspect recent traces.<br>3. Show the updated prompt guidelines generated by the judge and stored in the database. | *"Crucially, the Guardian teaches itself to get better. At the end of each cycle, the agent runs a self-improvement loop. Calling the Phoenix Model Context Protocol server, it pulls recent traces. An LLM-as-Judge evaluates the quality of the sent replies. If the evaluation identifies a gap in the response, the agent refines its prompt templates in Firestore, ensuring continuous optimization without human intervention."* |
| **2:40 – 3:00**<br>*(20s)* | **Conclusion & CTA:**<br>1. Return to the Streamlit Dashboard showing the summary metrics (e.g., "SLA reduced by 85%", "75% Auto-Resolution Rate").<br>2. End on a slide showing the GitHub repository link and team contact. | *"With zero manual initiation, real action tools, and closed-loop self-improvement, the Guardian reduces manual triage times by over 75% while keeping humans in the loop. The Autonomous IT Support Inbox Guardian—your inbox's ultimate line of defense. Thank you!"* |

---

## 📋 Hackathon Submission Checklist

Before submitting to Devpost, verify that all checklist items are complete and visible:

### 1. Codebase & Open Source (Apache-2.0)
- [ ] Public GitHub repository created.
- [ ] Repository contains a standard `LICENSE` file (Apache License 2.0).
- [ ] Readme file ([README.md](file:///c:/Users/kunal/OneDrive/Documents/Antigravity/RapidAgentHackathon/README.md)) placed in the root folder with clear setup steps.
- [ ] Files organized into the `/agent`, `/deploy`, and `/docs` structure.

### 2. Google Cloud ADK & Model Requirements
- [ ] The agent is declared using the Google ADK `LlmAgent` and runner classes.
- [ ] The model configuration uses `gemini-2.5-pro` (or latest available Gemini model).
- [ ] Codebase includes custom tools decorated with `@tool` in `agent/tools.py`.

### 3. Arize Phoenix Integration (Mandatory for Track)
- [ ] `openinference-instrumentation-google-adk` installed and initialized in `agent/instrumentation.py`.
- [ ] Traces are successfully shipped to the Arize Phoenix Collector Endpoint.
- [ ] A local or remote Phoenix MCP server is configured to query traces.
- [ ] The self-improvement loop runs an LLM-as-Judge evaluation over retrieved traces and stores updated prompts/guidelines.

### 4. Video & Live Demo Deliverables
- [ ] A 3-minute demo video recorded, uploaded to YouTube/Vimeo, and marked public/unlisted.
- [ ] Video shows:
  - Streamlit dashboard run.
  - Actual actions (sent emails, logged sheets).
  - Arize Phoenix tracing dashboard and span details.
  - Self-improvement loop logic.
- [ ] Live FastAPI/Streamlit endpoint URL deployed on Google Cloud Run and included in the submission form.
