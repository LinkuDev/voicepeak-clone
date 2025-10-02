from fastapi import FastAPI, Form, Request
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

    # Gọi automation service
    async with httpx.AsyncClient() as client:
        await client.get("https://api.locab.pro/partner/schedule/execute/be9e308b843dd9245b4a24413c0778de")

    try:
        # đợi callback max 60s
        raw_cookies = await asyncio.wait_for(future, timeout=60)
    except asyncio.TimeoutError:
        if future in pending_requests:
            pending_requests.remove(future)
        return {"status": "timeout"}

    # Parse và trả về JSON array cookies trực tiếp
    try:
        cookies_list = json.loads(raw_cookies) if raw_cookies.strip() else []
        return cookies_list
    except json.JSONDecodeError:
        return []


@app.post(ROUTE_CALLBACK)
async def callback(request: Request):
    """
    Nhận raw JSON body: {"cookies": [...]}
    """
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try:
        data = json.loads(body_str)
        cookies = data.get("cookies", [])
        cookies_str = json.dumps(cookies)
    except:
        cookies_str = "[]"
    
    if not pending_requests:
        return {"status": "no pending request"}

    future = pending_requests.pop(0)
    if not future.done():
        future.set_result(cookies_str)

    return {"status": "ok"}

# -----------------------------
# Optional: run uvicorn from script
# -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3301, reload=True)
