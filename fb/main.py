from fastapi import FastAPI, Form
from pydantic import BaseModel
import asyncio
import json
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
async def callback(cookies: str = Form(...)):
    """
    cookies: JSON string gửi từ form data, ví dụ:
    '{"c_user":"123","xs":"abcd"}'
    """
    try:
        cookies_dict: Dict[str, Any] = json.loads(cookies)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON in cookies"}

    if not pending_requests:
        return {"status": "no pending request"}

    # Lấy Future đầu tiên trong queue (FIFO)
    future = pending_requests.pop(0)
    if not future.done():
        future.set_result(cookies_dict)
        print("[CALLBACK] Callback received from form data, notified first GET request")

    return {"status": "ok"}

# -----------------------------
# Optional: run uvicorn from script
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3301, reload=True)
