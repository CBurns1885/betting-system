import time
class Timer:
    def __init__(self, label=""):
        self.label = label
    def __enter__(self):
        self.start = time.time()
        if self.label:
            print(f"⏱️  {self.label}...")
        return self
    def __exit__(self, *args):
        if self.label:
            print(f"✅ {self.label} done in {time.time()-self.start:.2f}s")
