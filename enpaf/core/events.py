"""
ENPAF Core — Events System
Pub/sub event system for application lifecycle and custom events.
"""

import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


class EventEmitter:
    """Thread-safe event emitter with support for lifecycle and custom events."""

    # Built-in lifecycle events
    LIFECYCLE_EVENTS = [
        "app_start",
        "app_stop",
        "app_pause",
        "app_resume",
        "app_error",
        "page_load",
        "page_unload",
        "bridge_connect",
        "bridge_disconnect",
    ]

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._once_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

    def on(self, event: str, handler: Callable) -> Callable:
        """
        Register a handler for an event.
        Can be used as a decorator:
        
            @events.on("app_start")
            def on_start():
                print("Started!")
        """
        with self._lock:
            self._handlers[event].append(handler)
        return handler

    def once(self, event: str, handler: Callable) -> Callable:
        """Register a handler that fires only once."""
        with self._lock:
            self._once_handlers[event].append(handler)
        return handler

    def off(self, event: str, handler: Optional[Callable] = None):
        """Remove a handler or all handlers for an event."""
        with self._lock:
            if handler is None:
                self._handlers[event].clear()
                self._once_handlers[event].clear()
            else:
                if handler in self._handlers[event]:
                    self._handlers[event].remove(handler)
                if handler in self._once_handlers[event]:
                    self._once_handlers[event].remove(handler)

    def emit(self, event: str, *args, **kwargs) -> List[Any]:
        """
        Emit an event, calling all registered handlers.
        Returns a list of handler return values.
        """
        results = []

        with self._lock:
            handlers = list(self._handlers.get(event, []))
            once_handlers = list(self._once_handlers.get(event, []))
            # Clear once handlers
            if event in self._once_handlers:
                self._once_handlers[event].clear()

        for handler in handlers + once_handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # Emit error event (avoid infinite recursion)
                if event != "app_error":
                    self.emit("app_error", e, event, handler)
                results.append(None)

        return results

    def has_listeners(self, event: str) -> bool:
        """Check if an event has any listeners."""
        with self._lock:
            return bool(
                self._handlers.get(event) or self._once_handlers.get(event)
            )

    def listener_count(self, event: str) -> int:
        """Get the number of listeners for an event."""
        with self._lock:
            return len(self._handlers.get(event, [])) + len(
                self._once_handlers.get(event, [])
            )

    def event_names(self) -> List[str]:
        """Get all event names with registered handlers."""
        with self._lock:
            names = set(self._handlers.keys()) | set(self._once_handlers.keys())
            return [n for n in names if self._handlers.get(n) or self._once_handlers.get(n)]
