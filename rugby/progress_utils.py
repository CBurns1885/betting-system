# progress_utils.py - Progress tracking utilities
import time
from contextlib import contextmanager

class Timer:
    def __init__(self, label: str = ""):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.time()
        if self.label:
            print(f"\n⏱️  {self.label}...")
        return self

    def __exit__(self, *args):
        elapsed = time.time() - self.start
        if self.label:
            print(f"✅ {self.label} completed in {elapsed:.2f}s")

def heartbeat(msg: str):
    """Print a simple status message"""
    print(f"  → {msg}")
