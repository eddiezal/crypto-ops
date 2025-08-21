import os
import requests

def _hdrs():
    return {
        "Authorization": f"Bearer {os.environ.get('RUN_TOKEN','')}",
        "x-app-key": os.environ.get("APP_KEY","")
    }

def test_plan_health():
    base = os.environ["RUN_URL"]
    r = requests.get(f"{base}/plan", headers=_hdrs())
    assert r.status_code == 200
    assert "actions" in r.json()

def test_metrics():
    base = os.environ["RUN_URL"]
    r = requests.get(f"{base}/metrics")
    assert r.status_code == 200
