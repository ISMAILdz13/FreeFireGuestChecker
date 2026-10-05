"""
Task Queue for Free Fire Guest Account Checker
Implements a thread-safe task queue with priority support
"""

from __future__ import annotations

import asyncio
import heapq
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp

logger = get_logger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass(order=True)
class Task:
    """A task to be executed by workers"""
    priority: int
    task_id: str = field(default_factory=lambda: generate_id("task"))
    callback: Callable = field(compare=False)
    args: Tuple = field(default_factory=tuple, compare=False)
    kwargs: Dict = field(default_factory=dict, compare=False)
    created_at: float = field(default_factory=time.time, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    timeout: float = field(default=60.0, compare=False)
    result: Optional[Any] = field(default=None, compare=False)
    error: Optional[Exception] = field(default=None, compare=False)
    completed: bool = field(default=False, compare=False)
    started_at: Optional[float] = field(default=None, compare=False)
    completed_at: Optional[float] = field(default=None, compare=False)

    def __post_init__(self):
        if isinstance(self.priority, TaskPriority):
            self.priority = self.priority.value

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "callback_name": getattr(self.callback, '__name__', str(self.callback)),
            "args": self.args,
            "kwargs": self.kwargs,
            "created_at": self.created_at,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "result": self.result,
            "error": str(self.error) if self.error else None,
            "completed": self.completed,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class TaskQueue:
    """Thread-safe task queue with priority support"""

    def __init__(self, max_size: int = 10000):
        self._queue: List[Task] = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._max_size = max_size
        self._running = True
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0
        }

    def enqueue(self, task: Task, block: bool = True, timeout: Optional[float] = None) -> bool:
        """Add a task to the queue"""
        with self._not_full:
            if not self._running:
                return False

            if len(self._queue) >= self._max_size:
                if not block:
                    return False
                if not self._not_full.wait(timeout):
                    return False

            heapq.heappush(self._queue, task)
            self._stats["enqueued"] += 1
            self._not_empty.notify()
            
        logger.debug(f"Task {task.task_id} enqueued with priority {task.priority}")
        return True

    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Task]:
        """Remove and return a task from the queue"""
        with self._not_empty:
            if not self._running:
                return None

            if not self._queue:
                if not block:
                    return None
                if not self._not_empty.wait(timeout):
                    return None

            task = heapq.heappop(self._queue)
            self._stats["dequeued"] += 1
            
        logger.debug(f"Task {task.task_id} dequeued")
        return task

    def peek(self) -> Optional[Task]:
        """Get the next task without removing it"""
        with self._lock:
            if self._queue:
                return self._queue[0]
            return None

    def mark_completed(self, task: Task, result: Any = None) -> None:
        """Mark a task as completed"""
        with self._lock:
            task.completed = True
            task.result = result
            task.completed_at = time.time()
            self._stats["completed"] += 1
        logger.debug(f"Task {task.task_id} completed")

    def mark_failed(self, task: Task, error: Exception = None) -> None:
        """Mark a task as failed"""
        with self._lock:
            task.completed = True
            task.error = error
            task.completed_at = time.time()
            self._stats["failed"] += 1
        logger.debug(f"Task {task.task_id} failed: {error}")

    def retry_task(self, task: Task) -> bool:
        """Retry a failed task"""
        with self._lock:
            if task.retries >= task.max_retries:
                return False

            task.retries += 1
            task.started_at = None
            task.completed_at = None
            task.error = None
            task.result = None
            task.completed = False
            
            self._stats["retrying"] += 1
            heapq.heappush(self._queue, task)
            self._not_empty.notify()
            
        logger.debug(f"Task {task.task_id} retry #{task.retries}")
        return True

    def size(self) -> int:
        """Get the current queue size"""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        with self._lock:
            return len(self._queue) == 0

    def is_full(self) -> bool:
        """Check if queue is full"""
        with self._lock:
            return len(self._queue) >= self._max_size

    def stop(self) -> None:
        """Stop the queue"""
        with self._lock:
            self._running = False
            self._not_empty.notify_all()
            self._not_full.notify_all()

    def clear(self) -> None:
        """Clear all tasks from the queue"""
        with self._lock:
            self._queue.clear()
            self._not_empty.notify_all()

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            return {
                **self._stats,
                "size": len(self._queue),
                "is_full": len(self._queue) >= self._max_size,
                "is_empty": len(self._queue) == 0,
                "running": self._running
            }

    def list_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List tasks in the queue"""
        with self._lock:
            return [task.to_dict() for task in self._queue[:limit]]


class AsyncTaskQueue:
    """Async task queue for asyncio-based workers"""

    def __init__(self, max_size: int = 10000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "completed": 0,
            "failed": 0,
            "retrying": 0
        }
        self._lock = asyncio.Lock()
        self._running = True

    async def enqueue(self, task: Task) -> bool:
        """Add a task to the queue"""
        if not self._running:
            return False

        await self._queue.put(task)
        async with self._lock:
            self._stats["enqueued"] += 1
        
        logger.debug(f"Async task {task.task_id} enqueued")
        return True

    async def dequeue(self) -> Optional[Task]:
        """Remove and return a task from the queue"""
        if not self._running:
            return None

        try:
            task = await self._queue.get()
            async with self._lock:
                self._stats["dequeued"] += 1
            logger.debug(f"Async task {task.task_id} dequeued")
            return task
        except asyncio.QueueEmpty:
            return None

    async def mark_completed(self, task: Task, result: Any = None) -> None:
        """Mark a task as completed"""
        async with self._lock:
            task.completed = True
            task.result = result
            task.completed_at = time.time()
            self._stats["completed"] += 1
        logger.debug(f"Async task {task.task_id} completed")

    async def mark_failed(self, task: Task, error: Exception = None) -> None:
        """Mark a task as failed"""
        async with self._lock:
            task.completed = True
            task.error = error
            task.completed_at = time.time()
            self._stats["failed"] += 1
        logger.debug(f"Async task {task.task_id} failed: {error}")

    async def retry_task(self, task: Task) -> bool:
        """Retry a failed task"""
        async with self._lock:
            if task.retries >= task.max_retries:
                return False

            task.retries += 1
            task.started_at = None
            task.completed_at = None
            task.error = None
            task.result = None
            task.completed = False
            
            self._stats["retrying"] += 1
            await self._queue.put(task)
            
        logger.debug(f"Async task {task.task_id} retry #{task.retries}")
        return True

    def size(self) -> int:
        """Get the current queue size"""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self._queue.empty()

    def is_full(self) -> bool:
        """Check if queue is full"""
        return self._queue.full()

    def stop(self) -> None:
        """Stop the queue"""
        self._running = False

    async def clear(self) -> None:
        """Clear all tasks from the queue"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self._stats,
            "size": self._queue.qsize(),
            "is_full": self._queue.full(),
            "is_empty": self._queue.empty(),
            "running": self._running
        }

    async def list_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List tasks in the queue"""
        tasks = []
        temp_queue = asyncio.Queue()
        
        # Drain the queue temporarily
        for _ in range(min(limit, self._queue.qsize())):
            try:
                task = self._queue.get_nowait()
                tasks.append(task.to_dict())
                await temp_queue.put(task)
            except asyncio.QueueEmpty:
                break
        
        # Restore the queue
        while not temp_queue.empty():
            task = await temp_queue.get()
            await self._queue.put(task)
        
        return tasks
