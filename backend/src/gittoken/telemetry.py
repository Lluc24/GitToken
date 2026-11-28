from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import HttpUrl

tracer = trace.get_tracer("gittoken")


def configure_tracing(endpoint: HttpUrl) -> None:
    provider = TracerProvider(resource=Resource.create({"service.name": "gittoken"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=str(endpoint))))
    trace.set_tracer_provider(provider)
