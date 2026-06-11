# Project Context & References: Autonomous IT Support Inbox Guardian

## Key Hackathon Details
- **Hackathon**: Google Cloud Rapid Agent Hackathon
- **Track**: Arize Track (requires Arize Phoenix tracing/MCP integration)
- **Goal**: Fully autonomous IT Support inbox agent that triages, auto-replies to routine tickets, escalates complex tickets, logs results, and self-improves via Phoenix LLM-as-Judge evals.
- **Tech Stack**: Python, Google Agent Development Kit (ADK), Arize Phoenix, FastAPI, Streamlit.

## Key Decisions & Constraints
1. **Phased Approach**: 
   - **Phase 1 (MVP - In Testing)**: FastAPI server, Streamlit dashboard, simulated sandbox mode (mock files), and Arize Phoenix tracing. Updated to remove purely client-side simulation, making the dashboard fully dynamic by fetching state from the backend.
   - **Phase 2 (Polish - Upcoming)**: Live Workspace API authentication, Google Cloud Run/Scheduler deployment.
2. **Dashboard Decisions**:
   - Streamlit will serve as the permanent dashboard (no custom HTML/CSS page migration required).
   - Added interactive testing controls (Mock Inbox Viewer and Send Test Email form) to support robust user testing.
   - Integrated dark/light mode toggle support.
3. **Model Configuration**:
   - Support model selection via `GEMINI_MODEL` environment variable.
4. **Supervisor Constraints**:
   - The supervisor agent (me) **must not write code** or perform execution steps directly.
   - Workspace modifications and development must be delegated to independent specialist subagents.

## Workspace & Remote Backup
- **Repository Remote**: `https://github.com/kunalkukrejadotcom/autonomous-it-support-inbox-guardian.git`
- **Security & Setup**: Vulnerability patches applied (CORS fixes, traceback sanitization, string validation, JSON safety).

## Specialist Agent Roles
1. **Setup Agent (Codebase Setup & Config)**: Sets up directory structures, dependency manifests, LICENSE, and base files. (Phase 1 completed)
2. **Core Agent Developer (ADK Backend)**: Implements FastAPI routes, tools (mock/live), instrumentation, prompts, and `GEMINI_MODEL` bindings.
3. **UI Developer (Streamlit Dashboard)**: Implements app dashboard, bindings to FastAPI, mock email creation, mock inbox viewer, and light/dark theme toggles.
4. **Docs Writer (Submission & Guides)**: Prepares README and Devpost submission scripts. (Phase 1 completed)
5. **QA & Verification Specialist**: Runs automated testing loops and startup validations.
6. **Git & Security Specialist**: Handles .gitignore, security audits, git initialization, and commits. (Phase 1 completed)

## Iterative Testing Strategy (Debug & Refine Loop)
To resolve run-time errors in the FastAPI `/process-inbox` execution path:
- **Loop Flow**:
  1. **QA Subagent**: Injects a new unread email using `POST /mock-db/email` (or mock database tools) and executes `POST /process-inbox`. Inspects logs and reports the exact exception/error.
  2. **Core Developer**: Resolves the bug in the backend code based on the QA report.
  3. **Verification**: QA subagent runs again to confirm success.
- **Goal**: Achieve a successful end-to-end simulated run loop with Gemini API execution and ensure the Arize Phoenix self-improvement trace analysis runs successfully.
- **Constraints**: Maximum of 10 cycles. All executions and fixes are delegated to the QA and Core Developer subagents.

## Current Progress (June 11, 2026)
- **Unread Status Bug Fix**:
  - Implemented `archive_email` in `agent/tools.py`.
  - Added `archive_email` to tools array in `agent/root_agent.py`.
  - Updated `agent/prompts/system_prompt.txt` to require `archive_email` call for escalated tickets (Complex Path).
  - Verified syntax matches and builds successfully.
- **Next Step**: Run the iterative QA & Verification Specialist loop to trigger `/process-inbox` and verify the fix works as expected.


