from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/myip")
def myip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return {"ip": r.json().get("ip")}
    except Exception as e:
        return {"error": str(e)}
