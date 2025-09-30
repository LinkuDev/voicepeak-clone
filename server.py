from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
import asyncio
import sqlite3
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware
from voicepeak_wrapper.voicepeak import Voicepeak, Narrator

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_BASE = os.path.join(BASE_DIR, "output_web")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(BASE_DIR, "users.db")

VOICE_CHOICES = [
    "Japanese Female Child",
    "Japanese Male 3",
    "Japanese Male 2",
    "Japanese Male 1",
    "Japanese Female 3",
    "Japanese Female 2",
    "Japanese Female 1"
]

# Helper: get narrator/emotion list
async def get_narrators():
    client = Voicepeak()
    return await client.get_narrator_list()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...)):
    username = username.strip()
    if not username:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Vui lòng nhập tên người dùng."})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (username,))
    if not c.fetchone():
        c.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
    conn.close()
    request.session["username"] = username
    return RedirectResponse("/voice", status_code=303)

@app.get("/voice", response_class=HTMLResponse)
async def voice_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("voice.html", {"request": request, "username": username, "voices": VOICE_CHOICES})

def say_text_sync(client, line, wav_path, voice):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.say_text(line, output_path=wav_path, narrator=voice))
    loop.close()

@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    voice: str = Form(...),
    text_content: str = Form(""),
    text_file: UploadFile = File(None)
):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/", status_code=303)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(STATIC_DIR, username, now_str)
    os.makedirs(output_path, exist_ok=True)
    if text_file:
        file_path = os.path.join(output_path, text_file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(text_file.file, f)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    else:
        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
    client = Voicepeak()
    output_txt_path = os.path.join(output_path, "voice_lines.txt")
    with open(output_txt_path, "w", encoding="utf-8") as txt_out:
        for idx, line in enumerate(lines):
            wav_path = os.path.join(output_path, f"voice_{idx}.wav")
            txt_path = os.path.join(output_path, f"text_{idx:02d}.txt")
            txt_out.write(f"{idx}: {line}\n")
            with open(txt_path, "w", encoding="utf-8") as single_txt:
                single_txt.write(line)
            try:
                await asyncio.to_thread(say_text_sync, client, line, wav_path, voice)
            except Exception as e:
                error_log = os.path.join(output_path, "error.log")
                with open(error_log, "a", encoding="utf-8") as err_file:
                    err_file.write(f"Lỗi tạo voice cho dòng {idx}: {line}\n{str(e)}\n")
    # Trả về thông báo thành công, không render danh sách file
    return templates.TemplateResponse("success.html", {
        "request": request,
        "output_path": output_path,
        "username": username,
        "voice": voice
    })
