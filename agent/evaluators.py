import os
import json
import datetime
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Find workspace root and prompt paths dynamically
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(CURRENT_DIR)
MOCK_EVALS_PATH = os.path.join(WORKSPACE_ROOT, "mock_evals.json")
MOCK_REPLIES_PATH = os.path.join(WORKSPACE_ROOT, "mock_replies.json")
MOCK_INBOX_PATH = os.path.join(WORKSPACE_ROOT, "mock_inbox.json")
SYSTEM_PROMPT_PATH = os.path.join(CURRENT_DIR, "prompts", "system_prompt.txt")
SELF_EVAL_PROMPT_PATH = os.path.join(CURRENT_DIR, "prompts", "self_eval_prompt.txt")

# Load environment variables
load_dotenv(os.path.join(WORKSPACE_ROOT, ".env"))

class TraceEvaluation(BaseModel):
    helpfulness_score: int = Field(..., description="Helpfulness score (1-5)")
    completeness_score: int = Field(..., description="Completeness score (1-5)")
    tone_score: int = Field(..., description="Tone & Professionalism score (1-5)")
    reasoning: str = Field(..., description="A concise explanation of the scores assigned.")
    improvement_recommendations: str = Field(..., description="Specific concrete suggestions to improve the response templates or classification rules.")

def ensure_eval_file_exists():
    """Seeds/manages mock_evals.json in the workspace root."""
    if not os.path.exists(MOCK_EVALS_PATH) or os.path.getsize(MOCK_EVALS_PATH) == 0:
        default_evals = []
        with open(MOCK_EVALS_PATH, "w", encoding="utf-8") as f:
            json.dump(default_evals, f, indent=2)

def fetch_traces(limit: int = 5):
    """Fetches recent traces from live Phoenix or fallback mock files."""
    traces = []
    
    # 1. Try to fetch from live Phoenix client
    try:
        from phoenix.client import Client
        # Derive base URL from env — strip trailing /v1/traces if present
        _phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
        _phoenix_base = os.getenv("PHOENIX_BASE_URL", "")
        if not _phoenix_base and _phoenix_endpoint:
            _phoenix_base = _phoenix_endpoint.replace("/v1/traces", "").rstrip("/")
        client = Client(base_url=_phoenix_base) if _phoenix_base else Client()
        spans_df = client.get_spans()
        if not spans_df.empty:
            # Filter for send_reply spans which represent the response sent to the customer
            send_reply_spans = spans_df[spans_df['name'] == 'send_reply']
            if not send_reply_spans.empty:
                if 'start_time' in send_reply_spans.columns:
                    send_reply_spans = send_reply_spans.sort_values(by='start_time', ascending=False)
                
                recent_spans = send_reply_spans.head(limit)
                
                # Load mock inbox to resolve query details if needed
                inbox_map = {}
                try:
                    if os.path.exists(MOCK_INBOX_PATH):
                        with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                            inbox = json.load(f)
                            inbox_map = {msg["id"]: msg for msg in inbox}
                except Exception:
                    pass
                
                for _, row in recent_spans.iterrows():
                    trace_id = row.get('context.trace_id') or row.get('trace_id', 'unknown_trace')
                    timestamp = str(row.get('start_time', datetime.datetime.now().isoformat()))
                    attributes = row.get('attributes') or {}
                    
                    reply_body = ""
                    message_id = ""
                    
                    # Parse parameters
                    if isinstance(attributes, dict):
                        input_val = attributes.get('input.value', '')
                        if input_val:
                            try:
                                params = json.loads(input_val)
                                reply_body = params.get('body', '')
                                message_id = params.get('message_id', '')
                            except Exception:
                                pass
                        
                        if not reply_body:
                            reply_body = attributes.get('tool.parameters.body') or attributes.get('body') or ""
                        if not message_id:
                            message_id = attributes.get('tool.parameters.message_id') or attributes.get('message_id') or ""
                    
                    query_text = ""
                    # Find corresponding root span of the same trace in spans_df
                    trace_col = 'context.trace_id' if 'context.trace_id' in spans_df.columns else 'trace_id'
                    if trace_col in spans_df.columns:
                        trace_spans = spans_df[spans_df[trace_col] == trace_id]
                        agent_spans = trace_spans[trace_spans['name'] == 'InboxGuardian']
                        if not agent_spans.empty:
                            agent_attr = agent_spans.iloc[0].get('attributes') or {}
                            query_text = agent_attr.get('input.value', '')
                            if query_text:
                                try:
                                    q_val = json.loads(query_text)
                                    if isinstance(q_val, dict):
                                        query_text = q_val.get('message', '') or q_val.get('text', query_text)
                                except Exception:
                                    pass
                    
                    # Fallback to mock inbox if query not found
                    if not query_text and message_id and message_id in inbox_map:
                        query_text = inbox_map[message_id].get('body', '')
                        
                    # Fallback to mock replies if reply body not found
                    if not reply_body and message_id:
                        try:
                            if os.path.exists(MOCK_REPLIES_PATH):
                                with open(MOCK_REPLIES_PATH, "r", encoding="utf-8") as f:
                                    replies = json.load(f)
                                    for rep in replies:
                                        if rep.get("original_message_id") == message_id:
                                            reply_body = rep.get("body", "")
                                            break
                        except Exception:
                            pass
                            
                    if query_text or reply_body:
                        traces.append({
                            "trace_id": str(trace_id),
                            "timestamp": timestamp,
                            "query": query_text or "No Query Found",
                            "reply": reply_body or "No Reply Found",
                            "action_taken": "Auto-Replied"
                        })
    except Exception as e:
        print(f"Error querying live Phoenix client: {e}")
        
    # 2. Fall back to mock files if traces list is empty
    if not traces:
        try:
            if os.path.exists(MOCK_REPLIES_PATH) and os.path.exists(MOCK_INBOX_PATH):
                with open(MOCK_REPLIES_PATH, "r", encoding="utf-8") as f:
                    replies = json.load(f)
                with open(MOCK_INBOX_PATH, "r", encoding="utf-8") as f:
                    inbox = json.load(f)
                
                inbox_map = {msg["id"]: msg for msg in inbox}
                for rep in replies:
                    orig_id = rep.get("original_message_id")
                    orig_msg = inbox_map.get(orig_id, {})
                    traces.append({
                        "trace_id": f"trace_{rep.get('reply_id')}",
                        "timestamp": rep.get("timestamp"),
                        "query": orig_msg.get("body", "No Query"),
                        "reply": rep.get("body", ""),
                        "action_taken": "Auto-Replied"
                    })
        except Exception as e:
            print(f"Error reading mock logs for traces: {e}")
            
    return traces[-limit:] if traces else []

def run_trace_evaluations(limit: int = 5):
    """Runs trace evaluations on recent traces using Gemini LLM-as-a-Judge."""
    ensure_eval_file_exists()
    
    try:
        with open(MOCK_EVALS_PATH, "r", encoding="utf-8") as f:
            existing_evals = json.load(f)
    except Exception:
        existing_evals = []
        
    existing_by_trace = {ev.get("trace_id"): ev for ev in existing_evals if ev.get("trace_id")}
    
    traces = fetch_traces(limit)
    
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    if os.path.exists(SELF_EVAL_PROMPT_PATH):
        with open(SELF_EVAL_PROMPT_PATH, "r", encoding="utf-8") as f:
            self_eval_prompt_template = f.read()
    else:
        self_eval_prompt_template = """
You are an LLM-as-Judge evaluator assessing the quality of responses generated by the IT Support Inbox Guardian.
Input trace format:
---
Customer Query: {query}
Agent Reply: {reply}
Action Taken: {action_taken}
---

Perform evaluation on the following three criteria:
1. Helpfulness (1-5): Does the response solve the user's issue or provide the most logical next troubleshooting steps?
2. Completeness (1-5): Does the response cover all aspects of the user's request?
3. Tone & Professionalism (1-5): Is the tone polite, supportive, corporate, and clear?
        """
        
    new_evals = []
    
    for trace in traces:
        trace_id = trace.get("trace_id")
        if trace_id in existing_by_trace:
            new_evals.append(existing_by_trace[trace_id])
            continue
            
        prompt = self_eval_prompt_template
        prompt = prompt.replace("{query}", trace.get("query", ""))
        prompt = prompt.replace("{reply}", trace.get("reply", ""))
        prompt = prompt.replace("{action_taken}", trace.get("action_taken", ""))
        
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TraceEvaluation,
                )
            )
            
            eval_data = json.loads(response.text)
            eval_data["trace_id"] = trace_id
            eval_data["timestamp"] = trace.get("timestamp") or datetime.datetime.now().isoformat()
            eval_data["customer_query"] = trace.get("query")
            eval_data["agent_reply"] = trace.get("reply")
            eval_data["action_taken"] = trace.get("action_taken")
            
            existing_evals.append(eval_data)
            existing_by_trace[trace_id] = eval_data
            new_evals.append(eval_data)
        except Exception as e:
            print(f"Error evaluating trace {trace_id}: {e}")
            
    with open(MOCK_EVALS_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_evals, f, indent=2)
        
    return new_evals

def clean_llm_prompt_output(text: str) -> str:
    """Strips code fence blocks from LLM generated prompt string."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text

def run_self_improvement():
    """Evaluates recent scores, compiles recommendations, and refines system prompt if needed."""
    ensure_eval_file_exists()
    
    try:
        with open(MOCK_EVALS_PATH, "r", encoding="utf-8") as f:
            evals = json.load(f)
    except Exception:
        evals = []
        
    if not evals:
        # Run evaluations on 5 recent traces to generate some initial scores
        evals = run_trace_evaluations(limit=5)
        
    if not evals:
        return {
            "status": "error",
            "message": "No evaluations found or generated to analyze for self-improvement.",
            "average_score": 0.0,
            "improved": False
        }
        
    recent_evals = evals[-5:]
    
    total_score = 0.0
    recommendations_list = []
    for ev in recent_evals:
        h_score = ev.get("helpfulness_score")
        if h_score is not None:
            h = float(h_score)
        else:
            h = float(ev.get("helpfulness", 0.0)) * 5.0
            
        c_score = ev.get("completeness_score")
        if c_score is not None:
            c = float(c_score)
        else:
            c = float(ev.get("completeness", 0.0)) * 5.0
            
        t_score = ev.get("tone_score")
        if t_score is not None:
            t = float(t_score)
        else:
            t = float(ev.get("tone", 0.0)) * 5.0
            
        total_score += (h + c + t) / 3.0
        
        rec = ev.get("improvement_recommendations") or ev.get("recommendation")
        if rec and rec.strip().lower() not in ["none", "none needed.", "no recommendations.", "none."]:
            recommendations_list.append(rec.strip())
            
    avg_score = total_score / len(recent_evals)
    
    result = {
        "status": "success",
        "average_score": round(avg_score, 2),
        "improved": False,
        "recommendations_compiled": recommendations_list
    }
    
    if avg_score < 4.0:
        if os.path.exists(SYSTEM_PROMPT_PATH):
            with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
                current_system_prompt = f.read()
        else:
            return {
                "status": "error",
                "message": "System prompt file not found.",
                "average_score": round(avg_score, 2),
                "improved": False
            }
            
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        recommendations_str = "\n".join([f"- {r}" for r in recommendations_list]) if recommendations_list else "- Improve overall response templates to be more helpful, complete, and polite."
        
        optimization_prompt = f"""
You are an expert prompt engineer. Your task is to refine the system prompt of an Autonomous IT Support Inbox Guardian agent.

Here is the current system prompt:
---
{current_system_prompt}
---

Here are the compiled improvement recommendations from the LLM-as-a-Judge evaluations:
---
{recommendations_str}
---

Please refine the operating guidelines, response templates, and classification rules in the system prompt to directly address these recommendations. Make sure the output is a drop-in replacement for the system prompt. Keep the overall structure and format of the prompt, but refine the guidelines, rules, or troubleshooting templates as suggested.

Return only the updated, optimized system prompt text. Do not wrap it in code blocks or include any introduction/explanation.
"""
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=optimization_prompt
            )
            
            new_prompt = response.text
            new_prompt = clean_llm_prompt_output(new_prompt)
            
            with open(SYSTEM_PROMPT_PATH, "w", encoding="utf-8") as f:
                f.write(new_prompt)
                
            result["improved"] = True
            result["old_prompt"] = current_system_prompt
            result["new_prompt"] = new_prompt
            result["message"] = f"Average score was {round(avg_score, 2)} < 4.0. System prompt successfully optimized based on feedback."
        except Exception as e:
            result["improved"] = False
            result["message"] = f"Failed to optimize system prompt: {str(e)}"
    else:
        result["message"] = f"Average score was {round(avg_score, 2)} >= 4.0. No improvement needed."
        
    return result
