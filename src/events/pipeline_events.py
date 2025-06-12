"""Event system for pipeline lifecycle events."""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional, Union
from datetime import datetime

logger = logging.getLogger("ducky.events.pipeline")


class PipelineEventType(Enum):
    """Types of pipeline lifecycle events."""
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed" 
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_CANCELLED = "pipeline_cancelled"


@dataclass
class PipelineEvent:
    """Data structure for pipeline events."""
    event_type: PipelineEventType
    project_id: int
    timestamp: datetime
    metadata: Dict[str, Any]
    
    @classmethod
    def create_started(cls, project_id: int, **metadata) -> 'PipelineEvent':
        """Create a pipeline started event."""
        return cls(
            event_type=PipelineEventType.PIPELINE_STARTED,
            project_id=project_id,
            timestamp=datetime.now(),
            metadata=metadata
        )
    
    @classmethod
    def create_completed(cls, project_id: int, **metadata) -> 'PipelineEvent':
        """Create a pipeline completed event."""
        return cls(
            event_type=PipelineEventType.PIPELINE_COMPLETED,
            project_id=project_id,
            timestamp=datetime.now(),
            metadata=metadata
        )
    
    @classmethod
    def create_failed(cls, project_id: int, error: str, **metadata) -> 'PipelineEvent':
        """Create a pipeline failed event."""
        return cls(
            event_type=PipelineEventType.PIPELINE_FAILED,
            project_id=project_id,
            timestamp=datetime.now(),
            metadata={"error": error, **metadata}
        )
    
    @classmethod
    def create_cancelled(cls, project_id: int, reason: str, **metadata) -> 'PipelineEvent':
        """Create a pipeline cancelled event."""
        return cls(
            event_type=PipelineEventType.PIPELINE_CANCELLED,
            project_id=project_id,
            timestamp=datetime.now(),
            metadata={"reason": reason, **metadata}
        )


class PipelineEventEmitter:
    """Event emitter for pipeline lifecycle events."""
    
    def __init__(self):
        self._listeners: Dict[PipelineEventType, List[Callable[[PipelineEvent], Any]]] = {}
        self._async_listeners: Dict[PipelineEventType, List[Callable[[PipelineEvent], Any]]] = {}
        self.logger = logger
    
    def on(self, event_type: PipelineEventType, listener: Callable[[PipelineEvent], Any]) -> None:
        """Register a synchronous event listener.
        
        Args:
            event_type: The type of event to listen for
            listener: Synchronous function to call when event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)
        self.logger.debug(f"Registered sync listener for {event_type.value}")
    
    def on_async(self, event_type: PipelineEventType, listener: Callable[[PipelineEvent], Any]) -> None:
        """Register an asynchronous event listener.
        
        Args:
            event_type: The type of event to listen for
            listener: Async function to call when event occurs
        """
        if event_type not in self._async_listeners:
            self._async_listeners[event_type] = []
        self._async_listeners[event_type].append(listener)
        self.logger.debug(f"Registered async listener for {event_type.value}")
    
    def off(self, event_type: PipelineEventType, listener: Callable[[PipelineEvent], Any]) -> bool:
        """Unregister an event listener.
        
        Args:
            event_type: The type of event
            listener: The listener function to remove
            
        Returns:
            bool: True if listener was found and removed, False otherwise
        """
        # Try sync listeners first
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            self.logger.debug(f"Removed sync listener for {event_type.value}")
            return True
        
        # Try async listeners
        if event_type in self._async_listeners and listener in self._async_listeners[event_type]:
            self._async_listeners[event_type].remove(listener)
            self.logger.debug(f"Removed async listener for {event_type.value}")
            return True
        
        return False
    
    def emit(self, event: PipelineEvent) -> None:
        """Emit an event to all registered listeners.
        
        Args:
            event: The event to emit
        """
        self.logger.info(f"Emitting event: {event.event_type.value} for project {event.project_id}")
        
        # Call synchronous listeners
        if event.event_type in self._listeners:
            for listener in self._listeners[event.event_type]:
                try:
                    listener(event)
                except Exception as e:
                    self.logger.error(f"Error in sync listener for {event.event_type.value}: {str(e)}")
        
        # Schedule async listeners
        if event.event_type in self._async_listeners:
            for listener in self._async_listeners[event.event_type]:
                try:
                    asyncio.create_task(listener(event))
                except Exception as e:
                    self.logger.error(f"Error scheduling async listener for {event.event_type.value}: {str(e)}")
    
    def emit_started(self, project_id: int, **metadata) -> None:
        """Convenience method to emit a pipeline started event."""
        event = PipelineEvent.create_started(project_id, **metadata)
        self.emit(event)
    
    def emit_completed(self, project_id: int, **metadata) -> None:
        """Convenience method to emit a pipeline completed event."""
        event = PipelineEvent.create_completed(project_id, **metadata)
        self.emit(event)
    
    def emit_failed(self, project_id: int, error: str, **metadata) -> None:
        """Convenience method to emit a pipeline failed event."""
        event = PipelineEvent.create_failed(project_id, error, **metadata)
        self.emit(event)
    
    def emit_cancelled(self, project_id: int, reason: str, **metadata) -> None:
        """Convenience method to emit a pipeline cancelled event."""
        event = PipelineEvent.create_cancelled(project_id, reason, **metadata)
        self.emit(event)
    
    def get_listener_count(self, event_type: Optional[PipelineEventType] = None) -> Union[int, Dict[PipelineEventType, int]]:
        """Get the number of listeners for an event type or all event types.
        
        Args:
            event_type: Specific event type, or None for all types
            
        Returns:
            int: Number of listeners for the event type
            Dict[PipelineEventType, int]: Listener counts for all event types
        """
        if event_type is not None:
            sync_count = len(self._listeners.get(event_type, []))
            async_count = len(self._async_listeners.get(event_type, []))
            return sync_count + async_count
        
        # Return counts for all event types
        counts = {}
        all_event_types = set(self._listeners.keys()) | set(self._async_listeners.keys())
        for et in all_event_types:
            sync_count = len(self._listeners.get(et, []))
            async_count = len(self._async_listeners.get(et, []))
            counts[et] = sync_count + async_count
        
        return counts


# Global event emitter instance
_global_emitter: Optional[PipelineEventEmitter] = None


def get_pipeline_event_emitter() -> PipelineEventEmitter:
    """Get the global pipeline event emitter instance.
    
    Returns:
        PipelineEventEmitter: The global event emitter
    """
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = PipelineEventEmitter()
        logger.debug("Created global pipeline event emitter")
    return _global_emitter


def reset_pipeline_event_emitter() -> None:
    """Reset the global event emitter (mainly for testing)."""
    global _global_emitter
    _global_emitter = None
    logger.debug("Reset global pipeline event emitter") 