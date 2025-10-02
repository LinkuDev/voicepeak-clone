from fastapi import FastAPI, Form
import asyncio
import httpx
import json
from typing import Any, List

ROUTE_START_TASK = "/start"
ROUTE_CALLBACK   = "/callback"

app = FastAPI(title="FB Cookies Service")
pending_requests = []

@app.get(ROUTE_START_TASK)
async def start_task():
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    pending_requests.append(future)

    # gọi automation service async
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.locab.pro/partner/schedule/execute/be9e308b843dd9245b4a24413c0778de")
        result = resp.json()
        print(f"[START] Automation response: {result}, waiting for callback...")

    try:
        # đợi callback max 60s
        raw_cookies = await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        if future in pending_requests:
            pending_requests.remove(future)
        return {"status": "timeout"}

    # Parse JSON string thành list cookies
    try:
        if raw_cookies.strip() == "":
            cookies_list: List[Any] = []
        else:
            # Nếu là JSON string, parse nó
            cookies_list = json.loads(raw_cookies)
            print(f"[START] Parsed {len(cookies_list)} cookies successfully")
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse cookies JSON: {e}")
        print(f"[ERROR] Raw cookies: {raw_cookies[:500]}")
        # Nếu không parse được, trả về raw string
        return {"status": "error", "message": "Invalid JSON", "raw": raw_cookies[:200]}

    return {"status": "done", "cookies": cookies_list}


@app.post(ROUTE_CALLBACK)
async def callback(cookies: str = Form(...)):
    """
    cookies: JSON string của array cookies, ví dụ '[{"name":"c_user","value":"123"}]'
    """
    if not pending_requests:
        print("[WARNING] Callback received but no pending request")
        return {"status": "no pending request"}

    future = pending_requests.pop(0)
    if not future.done():
        future.set_result(cookies)
        print(f"[CALLBACK] Received cookies: {cookies[:200]}...")  # Log first 200 chars

    return {"status": "ok"}

# -----------------------------
# Optional: run uvicorn from script
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3301, reload=True)
