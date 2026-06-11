import os
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

def instrument():
    """Initializes Phoenix OTEL tracing using openinference-instrumentation-google-adk."""
    # Read the collector endpoint from the environment, fallback to local Phoenix server default
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    project_name = "it-support-inbox-guardian"
    
    register(
        project_name=project_name,
        endpoint=endpoint,
        auto_instrument=True,
    )
    
    # Auto-instrument Google ADK
    GoogleADKInstrumentor().instrument()
