# Project Context & References: Autonomous IT Support Inbox Guardian

## Key Hackathon Details
- **Hackathon**: Google Cloud Rapid Agent Hackathon
- **Track**: Arize Track (requires Arize Phoenix tracing/MCP integration)
- **Goal**: Fully autonomous IT Support inbox agent that triages, auto-replies to routine tickets, escalates complex tickets, logs results, and self-improves via Phoenix LLM-as-Judge evals.
- **Tech Stack**: Python, Google Agent Development Kit (ADK), Arize Phoenix, FastAPI, Streamlit.

## Key Decisions & Constraints
1. **Phased Approach**: 
   - **Phase 1 (MVP - Completed)**: Streamlit dashboard, simulated sandbox mode (mock Gmail/Sheets via local files), and local Phoenix tracing. All core development and local compilation/startup tests completed.
   - **Phase 2 (Polish - Upcoming)**: Live Workspace API authentication, custom HTML/CSS web dashboard, GCP Cloud Run/Scheduler deployment.
2. **Supervisor Constraints**:
   - The supervisor agent (me) **must not write code** or perform execution steps directly.
   - All workspace setup, agent development, dashboard creation, and documentation must be delegated to independent specialist subagents.
   - The workload is broken down into parallel, non-overlapping tasks for specialist subagents.

## Workspace & Remote Backup
- **Repository Remote**: `https://github.com/kunalkukrejadotcom/autonomous-it-support-inbox-guardian.git`
- **Security & Setup**: Undergoing vulnerability scanning, `.gitignore` creation, and codebase git backup.

## Specialist Agent Roles
1. **Setup Agent (Codebase Setup & Config)**: Sets up directory structures, dependency manifests (`pyproject.toml`, `.env.example`), LICENSE (Apache-2.0), and base file skeletons. (Phase 1 completed)
2. **Core Agent Developer (ADK Backend)**: Implements `main.py`, `root_agent.py`, `instrumentation.py`, `tools.py` (with simulated mode), and text prompt templates. (Phase 1 completed)
3. **UI Developer (Streamlit Dashboard)**: Implements `agent/dashboard/app.py` connecting the frontend controls to the backend runner. (Phase 1 completed)
4. **Docs Writer (Submission & Guides)**: Prepares `README.md` and `docs/submission_notes.md` (video script + Devpost responses). (Phase 1 completed)
5. **QA & Verification Specialist**: Executes automated compile checks, runs uvicorn/streamlit startup scripts, validates APIs, and generates walkthrough reports. (Phase 1 completed)
6. **Git & Security Specialist**: Handles `.gitignore` creation, vulnerability/security fixes, git repo initialization, commits, and pushing code to the remote repository. (In progress)
