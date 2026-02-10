"""Background worker for async task processing."""
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Thread-based background task queue for non-blocking operations."""
    
    def __init__(self, num_threads: int = 4):
        self.num_threads = num_threads
        self.task_queue: queue.Queue = queue.Queue()
        self.workers: list[threading.Thread] = []
        self.running = False
        self.results: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
    def start(self) -> None:
        """Start worker threads."""
        if self.running:
            return
            
        self.running = True
        for i in range(self.num_threads):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"BackgroundWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        logger.info("Started %d background worker threads", self.num_threads)
    
    def stop(self) -> None:
        """Stop worker threads."""
        self.running = False
        # Send stop signals
        for _ in range(self.num_threads):
            self.task_queue.put(None)
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5.0)
        self.workers.clear()
        logger.info("Stopped background workers")
    
    def submit(
        self,
        task_id: str,
        func: Callable,
        *args,
        callback: Optional[Callable] = None,
        **kwargs
    ) -> None:
        """
        Submit a task for background processing.
        
        Args:
            task_id: Unique identifier for this task
            func: Function to execute
            *args: Positional arguments for func
            callback: Optional callback to execute with result
            **kwargs: Keyword arguments for func
        """
        self.task_queue.put({
            "task_id": task_id,
            "func": func,
            "args": args,
            "kwargs": kwargs,
            "callback": callback,
            "submitted_at": time.time()
        })
        logger.debug("Submitted task: %s", task_id)
    
    def get_result(self, task_id: str) -> Optional[Any]:
        """Get result of a completed task."""
        with self.lock:
            return self.results.get(task_id)
    
    def _worker_loop(self) -> None:
        """Main worker loop."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1.0)
                if task is None:  # Stop signal
                    break
                    
                self._process_task(task)
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as exc:
                logger.error("Worker error: %s", exc)
    
    def _process_task(self, task: Dict[str, Any]) -> None:
        """Process a single task."""
        task_id = task["task_id"]
        func = task["func"]
        args = task["args"]
        kwargs = task["kwargs"]
        callback = task.get("callback")
        
        try:
            logger.debug("Processing task: %s", task_id)
            result = func(*args, **kwargs)
            
            with self.lock:
                self.results[task_id] = {
                    "status": "success",
                    "result": result,
                    "completed_at": time.time()
                }
            
            if callback:
                try:
                    callback(result)
                except Exception as exc:
                    logger.error("Callback error for %s: %s", task_id, exc)
                    
        except Exception as exc:
            logger.error("Task %s failed: %s", task_id, exc)
            with self.lock:
                self.results[task_id] = {
                    "status": "error",
                    "error": str(exc),
                    "completed_at": time.time()
                }


# Global worker instance
_worker: Optional[BackgroundWorker] = None
_worker_lock = threading.Lock()


def get_worker() -> BackgroundWorker:
    """Get or create the global background worker."""
    global _worker
    
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                _worker = BackgroundWorker(num_threads=4)
                _worker.start()
    
    return _worker


def submit_task(
    task_id: str,
    func: Callable,
    *args,
    callback: Optional[Callable] = None,
    **kwargs
) -> None:
    """Submit a task to the global background worker."""
    worker = get_worker()
    worker.submit(task_id, func, *args, callback=callback, **kwargs)


def get_task_result(task_id: str) -> Optional[Any]:
    """Get result of a completed task."""
    worker = get_worker()
    return worker.get_result(task_id)
