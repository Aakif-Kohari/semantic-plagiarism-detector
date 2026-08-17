import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.api.app import app

@pytest.fixture(autouse=True)
def memory_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    
    # Store the original provider
    original_provider = trace.get_tracer_provider()
    
    # Set the new test provider
    trace.set_tracer_provider(provider)
    
    yield exporter
    
    # Restore the original provider
    trace.set_tracer_provider(original_provider)


def test_otel_middleware_records_exception(memory_exporter):
    """
    Test that the otel_tracing_middleware catches an exception from a route,
    records it in the span, sets http.status_code to 500, and re-raises.
    """
    client = TestClient(app, raise_server_exceptions=True)
    
    @app.get("/_test_error")
    async def test_error():
        raise ValueError("Intentional error for testing")

    # The exception should be propagated back to the TestClient
    with pytest.raises(ValueError, match="Intentional error"):
        client.get("/_test_error")

    spans = memory_exporter.get_finished_spans()
    assert len(spans) > 0, "No spans were exported"
    
    # Find our HTTP span
    http_span = next((span for span in spans if span.name == "HTTP GET /_test_error"), None)
    assert http_span is not None, "Could not find HTTP span for the route"
    
    # Check that status code is 500
    attributes = http_span.attributes
    assert attributes.get("http.status_code") == 500

    # Check exception events
    events = http_span.events
    assert len(events) > 0, "No events recorded on the span"
    
    exception_event = next((e for e in events if e.name == "exception"), None)
    assert exception_event is not None, "No exception event recorded"
    
    assert exception_event.attributes.get("exception.type") == "ValueError"
    assert "Intentional error for testing" in exception_event.attributes.get("exception.message", "")
