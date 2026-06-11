import os
from google.adk.agents import LlmAgent
from .tools import read_unread_emails, send_reply, create_ticket_record, query_phoenix_traces

# Resolve system prompt path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
system_prompt_path = os.path.join(current_dir, "prompts", "system_prompt.txt")

with open(system_prompt_path, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Configurable model name via environment, fallback to standard gemini-2.5-flash
model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")

inbox_guardian = LlmAgent(
    model=model_name,
    name="InboxGuardian",
    description="Autonomous IT Support Inbox Guardian that triages and resolves IT support tickets.",
    instruction=SYSTEM_PROMPT,
    tools=[read_unread_emails, send_reply, create_ticket_record, query_phoenix_traces],
    output_key="final_action_plan"
)
