"""
Worker Pool for Free Fire Guest Account Checker
Implements a pool of workers for concurrent task processing
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from src.workers.queue import Task, TaskQueue, TaskPriority
from src.utils.logging import get_logger
from src.utils.helpers import generate_id, get_timestamp

logger = get_logger(__name__)


@dataclass
class WorkerStats:
    """Worker statistics"""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0
    total_time: float = 0.0
    last_task_at: Optional[float] = None
    started_at: float = field(default_factory=time.time)


class Worker:
    """A worker that processes tasks from a queue"""

    def __init__(self, worker_id: str, queue: TaskQueue, 
                 on_task_start: Optional[Callable] = None,
                 on_task_complete: Optional[Callable] = None,
                 on_task_fail: Optional[Callable] = None):
        self.worker_id = worker_id
        self.queue = queue
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete
        self.on_task_fail = on_task_fail
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.stats = WorkerStats(worker_id=worker_id)

    def start(self) -> None:
        """Start the worker"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Worker {self.worker_id} started")

    def stop(self) -> None:
        """Stop the worker"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info(f"Worker {self.worker_id} stopped")

    def _run(self) -> None:
        """Worker main loop"""
        while self._running:
            try:
                # Get task from queue
                task = self.queue.dequeue(block=True, timeout=1.0)
                if task is None:
                    continue

                # Execute task
                self._execute_task(task)

            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")

    def _execute_task(self, task: Task) -> None:
        """Execute a task"""
        task.started_at = time.time()
        
        if self.on_task_start:
            self.on_task_start(self, task)

        try:
            # Execute the task callback
            start_time = time.time()
            result = task.callback(*task.args, **task.kwargs)
            elapsed = time.time() - start_time
            
            self.queue.mark_completed(task, result)
            self.stats.tasks_completed += 1
            self.stats.total_time += elapsed
            self.stats.last_task_at = time.time()
            
            if self.on_task_complete:
                self.on_task_complete(self, task, result)
            
            logger.debug(f"Worker {self.worker_id} completed task {task.task_id} in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Worker {self.worker_id} task {task.task_id} failed: {e}")
            
            self.queue.mark_failed(task, e)
            self.stats.tasks_failed += 1
            
            # Check if we should retry
            if task.retries < task.max_retries:
                self.queue.retry_task(task)
                self.stats.tasks_retried += 1
            
            if self.on_task_fail:
                self.on_task_fail(self, task, e)

    def is_running(self) -> bool:
        """Check if worker is running"""
        return self._running


class AsyncWorker:
    """An async worker that processes tasks from an async queue"""

    def __init__(self, worker_id: str, queue: Any,
                 on_task_start: Optional[Callable] = None,
                 on_task_complete: Optional[Callable] = None,
                 on_task_fail: Optional[Callable] = None):
        self.worker_id = worker_id
        self.queue = queue
        self.on_task_start = on_task_start
        self.on_task_complete = on_task_complete
        self.on_task_fail = on_task_fail
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.stats = WorkerStats(worker_id=worker_id)

    async def start(self) -> None:
        """Start the async worker"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info(f"Async worker {self.worker_id} started")

    async def stop(self) -> None:
        """Stop the async worker"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Async worker {self.worker_id} stopped")

    async def _run(self) -> None:
        """Worker main loop"""
        while self._running:
            try:
                # Get task from queue
                task = await self.queue.dequeue()
                if task is None:
                    await asyncio.sleep(0.1)
                    continue

                # Execute task
                await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Async worker {self.worker_id} error: {e}")

    async def _execute_task(self, task: Task) -> None:
        """Execute a task"""
        task.started_at = time.time()
        
        if self.on_task_start:
            self.on_task_start(self, task)

        try:
            # Execute the task callback
            start_time = time.time()
            
            # Check if callback is async
            if asyncio.iscoroutinefunction(task.callback):
                result = await task.callback(*task.args, **task.kwargs)
            else:
                result = task.callback(*task.args, **task.kwargs)
            
            elapsed = time.time() - start_time
            
            await self.queue.mark_completed(task, result)
            self.stats.tasks_completed += 1
            self.stats.total_time += elapsed
            self.stats.last_task_at = time.time()
            
            if self.on_task_complete:
                self.on_task_complete(self, task, result)
            
            logger.debug(f"Async worker {self.worker_id} completed task {task.task_id} in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Async worker {self.worker_id} task {task.task_id} failed: {e}")
            
            await self.queue.mark_failed(task, e)
            self.stats.tasks_failed += 1
            
            # Check if we should retry
            if task.retries < task.max_retries:
                await self.queue.retry_task(task)
                self.stats.tasks_retried += 1
            
            if self.on_task_fail:
                self.on_task_fail(self, task, e)

    def is_running(self) -> bool:
        """Check if worker is running"""
        return self._running


class WorkerPool:
    """Pool of workers for concurrent task processing"""

    def __init__(self, num_workers: int = 4, queue_size: int = 10000,
                 use_async: bool = False):
        self.num_workers = num_workers
        self.use_async = use_async
        self.workers: List[Union[Worker, AsyncWorker]] = []
        
        if use_async:
            from src.workers.queue import AsyncTaskQueue
            self.queue = AsyncTaskQueue(max_size=queue_size)
        else:
            self.queue = TaskQueue(max_size=queue_size)
        
        self._running = False
        self._executor: Optional[ThreadPoolExecutor] = None
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retrying_tasks": 0,
            "avg_task_time": 0.0
        }

    def start(self) -> None:
        """Start the worker pool"""
        if self._running:
            return

        self._running = True
        
        # Create workers
        for i in range(self.num_workers):
            worker_id = f"worker_{i+1}"
            if self.use_async:
                worker = AsyncWorker(
                    worker_id=worker_id,
                    queue=self.queue,
                    on_task_start=self._on_task_start,
                    on_task_complete=self._on_task_complete,
                    on_task_fail=self._on_task_fail
                )
            else:
                worker = Worker(
                    worker_id=worker_id,
                    queue=self.queue,
                    on_task_start=self._on_task_start,
                    on_task_complete=self._on_task_complete,
                    on_task_fail=self._on_task_fail
                )
            
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Worker pool started with {self.num_workers} workers")

    def stop(self) -> None:
        """Stop the worker pool"""
        self._running = False
        
        for worker in self.workers:
            if self.use_async:
                asyncio.run_coroutine_threadsafe(worker.stop(), asyncio.get_event_loop())
            else:
                worker.stop()
        
        self.workers.clear()
        self.queue.stop()
        
        logger.info("Worker pool stopped")

    def submit(self, callback: Callable, *args: Any, **kwargs: Any) -> Optional[Task]:
        """Submit a task to the pool"""
        if not self._running:
            return None

        task = Task(
            priority=TaskPriority.NORMAL.value,
            callback=callback,
            args=args,
            kwargs=kwargs,
            timeout=kwargs.pop('timeout', 60.0)
        )
        
        if self.use_async:
            asyncio.run_coroutine_threadsafe(self.queue.enqueue(task), asyncio.get_event_loop())
        else:
            self.queue.enqueue(task)
        
        self._stats["total_tasks"] += 1
        logger.debug(f"Task {task.task_id} submitted to pool")
        
        return task

    def submit_high_priority(self, callback: Callable, *args: Any, **kwargs: Any) -> Optional[Task]:
        """Submit a high priority task"""
        if not self._running:
            return None

        task = Task(
            priority=TaskPriority.HIGH.value,
            callback=callback,
            args=args,
            kwargs=kwargs,
            timeout=kwargs.pop('timeout', 30.0)
        )
        
        if self.use_async:
            asyncio.run_coroutine_threadsafe(self.queue.enqueue(task), asyncio.get_event_loop())
        else:
            self.queue.enqueue(task)
        
        self._stats["total_tasks"] += 1
        logger.debug(f"High priority task {task.task_id} submitted")
        
        return task

    def submit_low_priority(self, callback: Callable, *args: Any, **kwargs: Any) -> Optional[Task]:
        """Submit a low priority task"""
        if not self._running:
            return None

        task = Task(
            priority=TaskPriority.LOW.value,
            callback=callback,
            args=args,
            kwargs=kwargs,
            timeout=kwargs.pop('timeout', 120.0)
        )
        
        if self.use_async:
            asyncio.run_coroutine_threadsafe(self.queue.enqueue(task), asyncio.get_event_loop())
        else:
            self.queue.enqueue(task)
        
        self._stats["total_tasks"] += 1
        logger.debug(f"Low priority task {task.task_id} submitted")
        
        return task

    async def submit_async(self, callback: Callable, *args: Any, **kwargs: Any) -> Optional[Task]:
        """Submit an async task"""
        if not self._running:
            return None

        task = Task(
            priority=TaskPriority.NORMAL.value,
            callback=callback,
            args=args,
            kwargs=kwargs,
            timeout=kwargs.pop('timeout', 60.0)
        )
        
        await self.queue.enqueue(task)
        self._stats["total_tasks"] += 1
        logger.debug(f"Async task {task.task_id} submitted")
        
        return task

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        queue_stats = self.queue.get_stats()
        
        worker_stats = {
            "workers": len(self.workers),
            "active_workers": sum(1 for w in self.workers if w.is_running()),
            "worker_details": [w.stats.to_dict() for w in self.workers]
        }
        
        return {
            **self._stats,
            "queue": queue_stats,
            "workers": worker_stats,
            "running": self._running
        }

    def _on_task_start(self, worker: Worker, task: Task) -> None:
        """Callback when task starts"""
        pass

    def _on_task_complete(self, worker: Worker, task: Task, result: Any) -> None:
        """Callback when task completes"""
        self._stats["completed_tasks"] += 1
        
        # Update average task time
        total_time = sum(w.stats.total_time for w in self.workers)
        total_tasks = sum(w.stats.tasks_completed for w in self.workers)
        if total_tasks > 0:
            self._stats["avg_task_time"] = total_time / total_tasks

    def _on_task_fail(self, worker: Worker, task: Task, error: Exception) -> None:
        """Callback when task fails"""
        self._stats["failed_tasks"] += 1

    def clear(self) -> None:
        """Clear all tasks from the queue"""
        self.queue.clear()
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retrying_tasks": 0,
            "avg_task_time": 0.0
        }

    def is_running(self) -> bool:
        """Check if pool is running"""
        return self._running

    def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete"""
        start_time = time.time()
        
        while self._running:
            queue_stats = self.queue.get_stats()
            
            if queue_stats["size"] == 0:
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            time.sleep(0.1)
        
        return True


class AsyncWorkerPool:
    """Async worker pool for asyncio-based processing"""

    def __init__(self, num_workers: int = 4, queue_size: int = 10000):
        self.num_workers = num_workers
        self.queue = None  # Will be initialized in start()
        self.workers: List[AsyncWorker] = []
        self._running = False
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retrying_tasks": 0,
            "avg_task_time": 0.0
        }

    async def start(self) -> None:
        """Start the async worker pool"""
        if self._running:
            return

        self._running = True
        self.queue = AsyncTaskQueue(max_size=queue_size)
        
        # Create workers
        for i in range(self.num_workers):
            worker_id = f"async_worker_{i+1}"
            worker = AsyncWorker(
                worker_id=worker_id,
                queue=self.queue,
                on_task_start=self._on_task_start,
                on_task_complete=self._on_task_complete,
                on_task_fail=self._on_task_fail
            )
            
            await worker.start()
            self.workers.append(worker)
        
        logger.info(f"Async worker pool started with {self.num_workers} workers")

    async def stop(self) -> None:
        """Stop the async worker pool"""
        self._running = False
        
        for worker in self.workers:
            await worker.stop()
        
        self.workers.clear()
        self.queue.stop()
        
        logger.info("Async worker pool stopped")

    async def submit(self, callback: Callable, *args: Any, **kwargs: Any) -> Optional[Task]:
        """Submit a task to the pool"""
        if not self._running:
            return None

        task = Task(
            priority=TaskPriority.NORMAL.value,
            callback=callback,
            args=args,
            kwargs=kwargs,
            timeout=kwargs.pop('timeout', 60.0)
        )
        
        await self.queue.enqueue(task)
        self._stats["total_tasks"] += 1
        logger.debug(f"Task {task.task_id} submitted to async pool")
        
        return task

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        queue_stats = self.queue.get_stats()
        
        worker_stats = {
            "workers": len(self.workers),
            "active_workers": sum(1 for w in self.workers if w.is_running()),
            "worker_details": [w.stats.to_dict() for w in self.workers]
        }
        
        return {
            **self._stats,
            "queue": queue_stats,
            "workers": worker_stats,
            "running": self._running
        }

    def _on_task_start(self, worker: AsyncWorker, task: Task) -> None:
        """Callback when task starts"""
        pass

    def _on_task_complete(self, worker: AsyncWorker, task: Task, result: Any) -> None:
        """Callback when task completes"""
        self._stats["completed_tasks"] += 1
        
        # Update average task time
        total_time = sum(w.stats.total_time for w in self.workers)
        total_tasks = sum(w.stats.tasks_completed for w in self.workers)
        if total_tasks > 0:
            self._stats["avg_task_time"] = total_time / total_tasks

    def _on_task_fail(self, worker: AsyncWorker, task: Task, error: Exception) -> None:
        """Callback when task fails"""
        self._stats["failed_tasks"] += 1

    async def clear(self) -> None:
        """Clear all tasks from the queue"""
        await self.queue.clear()
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retrying_tasks": 0,
            "avg_task_time": 0.0
        }

    def is_running(self) -> bool:
        """Check if pool is running"""
        return self._running

    async def wait_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete"""
        start_time = time.time()
        
        while self._running:
            queue_stats = self.queue.get_stats()
            
            if queue_stats["size"] == 0:
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            await asyncio.sleep(0.1)
        
        return True
