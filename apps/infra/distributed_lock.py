import os
import time
import json
from pathlib import Path
from typing import Optional

class FileLock:
    """File-based distributed lock for single-machine safety"""
    
    def __init__(self, name: str, timeout: int = 30):
        self.name = name
        self.timeout = timeout
        self.lock_dir = Path("locks")
        self.lock_dir.mkdir(exist_ok=True)
        self.lock_file = self.lock_dir / f"{name}.lock"
        self.instance_id = f"{os.getpid()}_{time.time()}"
    
    def acquire(self, blocking: bool = False, timeout: Optional[int] = None) -> bool:
        """Try to acquire lock"""
        timeout = timeout or self.timeout
        start = time.time()
        
        while True:
            try:
                # Check if existing lock is expired
                if self.lock_file.exists():
                    with open(self.lock_file, 'r') as f:
                        lock_data = json.load(f)
                    
                    if time.time() - lock_data["timestamp"] > lock_data["timeout"]:
                        # Lock expired, we can take it
                        self.lock_file.unlink()
                    elif not blocking:
                        return False
                    else:
                        time.sleep(0.1)
                        if time.time() - start > timeout:
                            return False
                        continue
                
                # Try to create lock atomically
                lock_data = {
                    "instance": self.instance_id,
                    "timestamp": time.time(),
                    "timeout": self.timeout
                }
                
                # Use exclusive create
                fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, json.dumps(lock_data).encode())
                os.close(fd)
                return True
                
            except FileExistsError:
                if not blocking:
                    return False
                time.sleep(0.1)
                if time.time() - start > timeout:
                    return False
            except Exception as e:
                print(f"Lock error: {e}")
                return False
    
    def release(self):
        """Release lock if we own it"""
        try:
            if self.lock_file.exists():
                with open(self.lock_file, 'r') as f:
                    lock_data = json.load(f)
                if lock_data["instance"] == self.instance_id:
                    self.lock_file.unlink()
        except Exception as e:
            print(f"Error releasing lock: {e}")
    
    def __enter__(self):
        if not self.acquire(blocking=True):
            raise RuntimeError(f"Could not acquire lock: {self.name}")
        return self
    
    def __exit__(self, *args):
        self.release()
