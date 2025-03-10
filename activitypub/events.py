import logging
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger(__name__)


def _get_fully_qualified_name(func: Callable):
    return f"{func.__module__}.{func.__name__}"


class EventSystem:
    EVENT_ACTIVITY = "activity"

    def __init__(self, initial_events=None):
        self.hooks: Dict[str, List[Callable]] = {}
        if initial_events:
            for event in initial_events:
                self.hooks[event] = []
        else:
            self.hooks = {"activity": []}

    def on(self, event_name: str):
        """Decorator for registering event handlers"""

        def decorator(func: Callable):
            self.register(event_name, func)
            return func

        return decorator

    def register(self, event_name: str, function: Callable):
        log.info(
            "Registering new function for event=%s function=%s",
            event_name,
            _get_fully_qualified_name(function),
        )

        """Register an event handler"""
        if event_name not in self.hooks:
            self.hooks[event_name] = []

        if not callable(function):
            raise ValueError("Function is not callable.")

        self.hooks[event_name].append(function)

    def unregister(self, event_name: str, function: Callable) -> bool:
        """Unregister an event handler"""
        if event_name not in self.hooks:
            return False

        if function in self.hooks[event_name]:
            self.hooks[event_name].remove(function)
            return True
        return False

    def fire(
        self, event_name: str, collect_results=False, **kwargs
    ) -> Optional[List[Any]]:
        """Fire an event and optionally collect results"""
        if event_name not in self.hooks:
            raise ValueError(
                f"Unsupported event {event_name}, must be one of {list(self.hooks.keys())}"
            )

        results = [] if collect_results else None

        for function in self.hooks[event_name]:
            try:
                result = function(**kwargs)
                if collect_results:
                    results.append(result)
            except Exception as e:
                log.error("Error in event handler %s: %s", {function.__name__}, e)

        return results


# Create a singleton instance
events = EventSystem(initial_events=[EventSystem.EVENT_ACTIVITY])

# Export the instance
__all__ = ["events"]
