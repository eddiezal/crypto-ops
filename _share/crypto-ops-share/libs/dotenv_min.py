import os, io

def load_dotenv(path: str = ".env", override: bool=True):
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): 
                    continue
                if "=" not in line: 
                    continue
                k,v = line.split("=",1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if override or (k not in os.environ):
                    os.environ[k] = v
    except FileNotFoundError:
        pass
