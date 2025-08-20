from fastapi import FastAPI
import requests, os

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/ip")
def ip():
    # Ask an external echo service; response will be NATed through your static egress IP
    try:
        r = requests.get("https://ifconfig.me/ip", timeout=5)
        r.raise_for_status()
        return {"egress_ip": r.text.strip()}
    except Exception as e:
        return {"error": str(e)}
