from opentelemetry import context as otel_context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from mcp.server.fastmcp import Context

_propagator = TraceContextTextMapPropagator()

def extract_context_from_mcp(ctx: Context):
    meta = ctx.request_context.meta
    if not meta:
        return otel_context.get_current()
    carrier = {}
    if getattr(meta, "traceparent", None):
        carrier["traceparent"] = meta.traceparent
    if getattr(meta, "tracestate", None):
        carrier["tracestate"] = meta.tracestate
    return _propagator.extract(carrier) if carrier else otel_context.get_current()