"""Observability port interface.

Contract between the application layer and observability backends (OpenTelemetry, App Insights).
Ref: TechSpec Section 2.1, lines 345-355
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IObservabilityPort(ABC):
    """Wraps OpenTelemetry for tracing, metrics, and logging.

    Lightweight abstraction for observability backends.
    """

    @abstractmethod
    def start_span(self, name: str, attributes: dict | None = None) -> object:
        """Start a tracing span.

        Args:
            name: Span name
            attributes: Optional span attributes

        Returns:
            Span context object (opaque to caller)
        """
        ...

    @abstractmethod
    def record_metric(self, name: str, value: float, tags: dict | None = None) -> None:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
            tags: Optional metric tags
        """
        ...

    @abstractmethod
    def log(self, level: str, message: str, **kwargs) -> None:
        """Log a message.

        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            **kwargs: Additional log context
        """
        ...
