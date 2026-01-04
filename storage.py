"""disk writer thread"""

import threading
import queue
import time


class StorageWorker:
    def __init__(self, v_log_file="history.log", v_flush_every=0.5):
        self.log_file = v_log_file
        self.flush_every = v_flush_every
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
    
    def stop(self, v_timeout=5):
        if not self._running:
            return
        self._running = False
        self._q.put(None)
        if self._thread:
            self._thread.join(v_timeout)
            if self._thread.is_alive():
                print("Warning: thread didnt stop")
            else:
                print(f"Storage stopped. Wrote {self._count} records")
    
    def enqueue(self, v_data):
        if self._running:
            self._q.put(v_data)
    
    def _loop(self):
        v_last = time.time()
        v_file = open(self.log_file, "a")
        try:
            while self._running or not self._q.empty():
                try:
                    v_item = self._q.get(timeout=self.flush_every)
                except queue.Empty:
                    if time.time() - v_last >= self.flush_every:
                        v_file.flush()
                        v_last = time.time()
                    continue
                
                if v_item is None:
                    break
                
                v_file.write(str(v_item) + "\n")
                with self._lock:
                    self._count += 1
                self._q.task_done()
                
                if time.time() - v_last >= self.flush_every:
                    v_file.flush()
                    v_last = time.time()
            
            v_file.flush()
        except IOError as e:
            print(f"Write error: {e}")
        finally:
            v_file.close()


class StorageStats:
    def __init__(self, v_worker):
        self.worker = v_worker
        self.started = time.time()
    
    def get_stats(self):
        v_elapsed = time.time() - self.started
        v_recs = self.worker.records_written
        return {
            "records_written": v_recs,
            "queue_size": self.worker.queue_size,
            "elapsed": v_elapsed,
            "rate": v_recs / v_elapsed if v_elapsed > 0 else 0
        }
    
    def print_stats(self):
        v_s = self.get_stats()
        print()
        print("--- Storage Stats ---")
        print(f"Written: {v_s['records_written']}")
        print(f"Queue: {v_s['queue_size']}")
        print(f"Time: {v_s['elapsed']:.1f}s")
        print(f"Rate: {v_s['rate']:.1f}/s")
