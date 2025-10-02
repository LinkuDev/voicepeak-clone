from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import requests
from typing import Any, Dict

# -----------------------------
# Define routes (by variables)
# -----------------------------
ROUTE_START_TASK = "/start"
ROUTE_CALLBACK   = "/callback"

# -----------------------------
# App setup
# -----------------------------
app = FastAPI(title="FB Cookies Service")

# -----------------------------
# Pending requests storage
# -----------------------------
# mỗi request GET sẽ tạo 1 Future, callback set result vào Future
pending_requests = []

# -----------------------------
# Pydantic model for callback
# -----------------------------
class CallbackData(BaseModel):
    cookies: Dict[str, Any]  # automation service trả JSON cookies

# -----------------------------
# GET /start-task
# -----------------------------
@app.get(ROUTE_START_TASK)
async def start_task():
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    pending_requests.append(future)

    # requests.post("http://automation-service/start")
    print("[START] Waiting for automation callback...")

    try:
        # đợi callback max 60s
        cookies = await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        pending_requests.remove(future)
        return {"status": "timeout"}

    return {"status": "done", "cookies": cookies}

# -----------------------------
# POST /callback
# -----------------------------
@app.post(ROUTE_CALLBACK)
async def callback(data: CallbackData):
    if not pending_requests:
        return {"status": "no pending request"}

    # Lấy Future đầu tiên (FIFO)
    future = pending_requests.pop(0)
    if not future.done():
        future.set_result(data.cookies)
        print("[CALLBACK] Callback received, notified GET request")
    return {"status": "ok"}

# -----------------------------
# Optional: run uvicorn from script
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3301, reload=True)
