import os, pytest, requests

def _hdrs():
    tok = os.environ.get("RUN_TOKEN","")
    return {"Authorization": f"Bearer {tok}"} if tok else {}

@pytest.mark.skipif(not os.environ.get("RUN_URL"), reason="RUN_URL not set")
def test_kill_switch_via_env():
    base = os.environ["RUN_URL"].rstrip("/")
    # simulate kill
    os.environ["KILL"] = "1"
    r = requests.get(f"{base}/plan", headers=_hdrs(), timeout=20); r.raise_for_status()
    data = r.json()
    assert data.get("actions") == []
    cfg = data.get("config", {})
    assert cfg.get("halted") is True
    assert (data.get("note") or "").startswith("KILLED")
    # clear kill
    os.environ.pop("KILL", None)
