from voicepeak_wrapper.util import say_text_sync

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
import os
import asyncio
from voicepeak_wrapper.voicepeak import Voicepeak

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

@router.post("/api/generate-line")
async def generate_line(
    request: Request,
    username: str = Form(...),
    voice: str = Form(...),
    line: str = Form(...),
    index: int = Form(...),
    time_key: str = Form(...)
):
    if not username or not line.strip() or not time_key:
        return JSONResponse({"error": "Thiếu thông tin."}, status_code=400)
    user_dir = os.path.join(STATIC_DIR, username, time_key)
    os.makedirs(user_dir, exist_ok=True)
    wav_path = os.path.join(user_dir, f"{index}.wav")
    txt_path = os.path.join(user_dir, f"{index:02d}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(line)
    client = Voicepeak()
    try:
        await asyncio.to_thread(say_text_sync, client, line, wav_path, voice)
    except Exception as e:
        # Ghi lỗi ra file error.log như server.py
        error_log = os.path.join(user_dir, "error.log")
        with open(error_log, "a", encoding="utf-8") as err_file:
            err_file.write(f"Lỗi tạo voice cho dòng {index}: {line}\n{str(e)}\n")
        return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({
        "wav_url": f"/static/{username}/{time_key}/{index}.wav",
        "index": index,
        "text": line
    })
