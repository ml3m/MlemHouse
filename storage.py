"""disk writer thread"""

import threading
import queue
import time


class StorageWorker:
    def __init__(self, log_file="history.log", flush_every=0.5):
        self.log_file = log_file
        self.flush_every = flush_every
        self._q = queue.Queue()
        self._thread = None
        self._running = False
        self._lock = threading.Lock()
        self._count = 0
    
    @property
    def records_written(self):
        with self._lock:
            return self._count
    
    @property
    def queue_size(self):
        return self._q.qsize()
    
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("Storage Thread Started...")
    
    def stop(self, timeout=5):
        if not self._running:
            return
        self._running = False
        self._q.put(None)
        if self._thread:
            self._thread.join(timeout)
            if self._thread.is_alive():
                print("Warning: thread didnt stop")
            else:
                print(f"Storage stopped. Wrote {self._count} records")
    
    def enqueue(self, data):
        if self._running:
            self._q.put(data)
    
    def _loop(self):
        last = time.time()
        f = open(self.log_file, "a")
        try:
            while self._running or not self._q.empty():
                try:
                    item = self._q.get(timeout=self.flush_every)
                except queue.Empty:
                    if time.time() - last >= self.flush_every:
                        f.flush()
                        last = time.time()
                    continue
                
                if item is None:
                    break
                
                f.write(str(item) + "\n")
                with self._lock:
                    self._count += 1
                self._q.task_done()
                
                if time.time() - last >= self.flush_every:
                    f.flush()
                    last = time.time()
            
            f.flush()
        except IOError as e:
            print(f"Write error: {e}")
        finally:
            f.close()


class StorageStats:
    def __init__(self, worker):
        self.worker = worker
        self.started = time.time()
    
    def get_stats(self):
        elapsed = time.time() - self.started
        recs = self.worker.records_written
        return {
            "records_written": recs,
            "queue_size": self.worker.queue_size,
            "elapsed": elapsed,
            "rate": recs / elapsed if elapsed > 0 else 0
        }
    
    def print_stats(self):
        s = self.get_stats()
        print()
        print("--- Storage Stats ---")
        print(f"Written: {s['records_written']}")
        print(f"Queue: {s['queue_size']}")
        print(f"Time: {s['elapsed']:.1f}s")
        print(f"Rate: {s['rate']:.1f}/s")
