import os, json, hashlib, subprocess, uuid, time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
CFG_PATH = BASE / "configs" / "policy.rebalancer.json"

def _git_commit():
    try:
        return subprocess.check_output(['git','rev-parse','--short','HEAD'], cwd=BASE).decode().strip()
    except Exception:
        return os.getenv('GIT_COMMIT','unknown')

def _config_load():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _config_hash(cfg: dict):
    try:
        s = json.dumps(cfg, sort_keys=True)
    except Exception:
        s = str(cfg)
    return hashlib.sha256(s.encode()).hexdigest()[:12]

def version_info():
    cfg = _config_load()
    return {
        "run_id": str(uuid.uuid4()),
        "code_commit": _git_commit(),
        "config_hash": _config_hash(cfg),
        "profile": cfg.get("profile","(unset)"),
        "image": os.getenv("K_REVISION","n/a"),      # Cloud Run revision if present
        "trading_mode": os.getenv("TRADING_MODE","paper"),
        "env": os.getenv("COINBASE_ENV","sandbox"),
        "ts": int(time.time())
    }
