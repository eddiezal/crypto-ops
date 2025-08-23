import os, requests

def _hdrs():
    return {"Authorization": f"Bearer {os.environ.get('RUN_TOKEN','')}"}

def test_plan_health():
    base = os.environ["RUN_URL"].rstrip("/")
    r = requests.get(f"{base}/plan", headers=_hdrs(), timeout=15)
    assert r.status_code == 200
    assert "actions" in r.json()

def test_metrics():
    base = os.environ["RUN_URL"].rstrip("/")
    r = requests.get(f"{base}/metrics", headers=_hdrs(), timeout=15)
    assert r.status_code == 200
