import os
import logging

logger = logging.getLogger(__name__)

# Module-level tracer provider reference
_tracer_provider = None


def instrument():
    """
    Initializes Phoenix OTEL tracing using openinference-instrumentation-google-adk.
    Uses phoenix.otel.register() which internally handles OTLP HTTP export.
    Gracefully degrades if Phoenix is unreachable or not configured.
    """
    global _tracer_provider

    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").strip()

    if not endpoint:
        logger.warning(
            "PHOENIX_COLLECTOR_ENDPOINT is not set — Phoenix tracing DISABLED."
        )
        return

    logger.info(f"Attempting Phoenix tracing init → {endpoint}")

    try:
        from phoenix.otel import register
        logger.info("phoenix.otel imported successfully")

        tracer_provider = register(
            project_name="it-support-inbox-guardian",
            endpoint=endpoint,
            auto_instrument=False,  # We instrument ADK manually below
        )
        logger.info(f"register() completed, provider: {type(tracer_provider).__name__}")

        try:
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor
            GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
            logger.info("GoogleADKInstrumentor applied successfully")
        except Exception as adk_err:
            logger.warning(f"GoogleADKInstrumentor failed (non-fatal): {adk_err}")

        _tracer_provider = tracer_provider
        logger.info(f"✅ Phoenix tracing ENABLED → {endpoint}")

    except Exception as e:
        logger.error(
            f"❌ Phoenix instrumentation FAILED: {type(e).__name__}: {e}",
            exc_info=True,
        )


def _send_test_span():
    """Emits a single test span to verify the OTLP pipeline is working."""
    if not _tracer_provider:
        logger.warning("Cannot send test span — tracer provider not initialized")
        return
    try:
        tracer = _tracer_provider.get_tracer("inbox-guardian-startup")
        with tracer.start_as_current_span("startup-health-check") as span:
            span.set_attribute("service.name", "inbox-guardian-api")
            span.set_attribute("startup.test", True)
        _tracer_provider.force_flush(timeout_millis=3000)
        logger.info("🔬 Startup test span flushed to Phoenix")
    except Exception as e:
        logger.warning(f"Test span failed (non-fatal): {e}")


def get_status() -> dict:
    """Returns current tracing status for the /health/tracing endpoint."""
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").strip()
    return {
        "tracing_enabled": _tracer_provider is not None,
        "endpoint": endpoint or "NOT SET",
        "provider_type": type(_tracer_provider).__name__ if _tracer_provider else None,
    }
