from fastapi import FastAPI, Form
import asyncio
import httpx
import json
from typing import Dict, Any

ROUTE_START_TASK = "/start"
ROUTE_CALLBACK   = "/callback"

app = FastAPI(title="FB Cookies Service")

# FIFO queue cho pending GET requests
pending_requests = []

# -----------------------------
# GET /start
# -----------------------------
@app.get(ROUTE_START_TASK)
async def start_task():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    pending_requests.append(future)

    # --- Gọi automation service async ---
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.locab.pro/partner/schedule/execute/be9e308b843dd9245b4a24413c0778de")
        result = resp.json()
        print(f"[START] Automation response: {result}, waiting for callback...")

    try:
        # đợi callback max 60s
        cookies = await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        if future in pending_requests:
            pending_requests.remove(future)
        return {"status": "timeout"}

    return {"status": "done", "cookies": cookies}

# -----------------------------
# POST /callback
# -----------------------------
@app.post(ROUTE_CALLBACK)
async def callback(cookies: str = Form(...)):
    """
    cookies: JSON string từ form data, ví dụ '{"c_user":"123","xs":"abcd"}'
    """
    try:
        cookies_dict: Dict[str, Any] = json.loads(cookies)
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON received: {cookies}")
        return {"status": "error", "message": "Invalid JSON in cookies"}

    if not pending_requests:
        print("[WARNING] Callback received but no pending request")
        return {"status": "no pending request"}

    # FIFO: lấy Future đầu tiên
    future = pending_requests.pop(0)
    if not future.done():
        future.set_result(cookies_dict)
        print(f"[CALLBACK] Received cookies: {cookies_dict}")

    return {"status": "ok"}

# -----------------------------
# Optional: run uvicorn from script
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3301, reload=True)
