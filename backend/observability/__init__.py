"""Observability, tracing, and audit logging package."""

from backend.observability.audit_log import AuditLogRecord, AuditTrail, build_audit_record, get_audit_trail
from backend.observability.logging import JsonLogFormatter, configure_logging, get_logger, log_event
from backend.observability.tracing import TraceRecorder, TraceSpan, get_trace_recorder

__all__ = [
    "AuditLogRecord",
    "AuditTrail",
    "JsonLogFormatter",
    "TraceRecorder",
    "TraceSpan",
    "build_audit_record",
    "configure_logging",
    "get_audit_trail",
    "get_logger",
    "get_trace_recorder",
    "log_event",
]
