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
import hashlib

# Mount new API router for interactive line-by-line API
from api_generate_line import router as api_generate_line_router


app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_BASE = os.path.join(BASE_DIR, "output_web")


app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Mount new API router
app.include_router(api_generate_line_router)
@app.get("/voice", response_class=HTMLResponse)
async def voice_interactive_page(request: Request):
    username = request.session.get("username")
    if not username:
        return RedirectResponse("/", status_code=303)
    is_admin = request.session.get("is_admin", False)
    return templates.TemplateResponse("voice_interactive.html", {
        "request": request, 
        "username": username,
        "is_admin": is_admin
    })

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
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    # Tạo admin mặc định nếu chưa có
    c.execute("SELECT username FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)", ("admin", admin_pass))
    conn.commit()
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip()
    if not username or not password:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Vui lòng nhập đầy đủ thông tin."})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed_pass = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT username, is_admin FROM users WHERE username=? AND password=?", (username, hashed_pass))
    user = c.fetchone()
    conn.close()
    if user:
        request.session["username"] = user[0]
        request.session["is_admin"] = bool(user[1])
        return RedirectResponse("voice", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Tên đăng nhập hoặc mật khẩu không đúng."})

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    username = request.session.get("username")
    is_admin = request.session.get("is_admin", False)
    if not username or not is_admin:
        return RedirectResponse("/", status_code=303)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, is_admin FROM users ORDER BY username")
    users = c.fetchall()
    conn.close()
    
    return templates.TemplateResponse("admin.html", {
        "request": request, 
        "username": username,
        "users": users
    })

@app.post("/admin/add-user", response_class=HTMLResponse)
async def add_user(request: Request, new_username: str = Form(...), new_password: str = Form(...), is_admin: int = Form(0)):
    username = request.session.get("username")
    if not username or not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    
    new_username = new_username.strip()
    if not new_username or not new_password:
        return RedirectResponse("../admin?error=empty", status_code=303)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        hashed_pass = hashlib.sha256(new_password.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", 
                  (new_username, hashed_pass, is_admin))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return RedirectResponse("../admin?error=exists", status_code=303)
    conn.close()
    return RedirectResponse("../admin?success=added", status_code=303)

@app.post("/admin/update-password", response_class=HTMLResponse)
async def update_password(request: Request, target_username: str = Form(...), new_password: str = Form(...)):
    username = request.session.get("username")
    if not username or not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    
    if not new_password:
        return RedirectResponse("../admin?error=empty", status_code=303)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed_pass = hashlib.sha256(new_password.encode()).hexdigest()
    c.execute("UPDATE users SET password=? WHERE username=?", (hashed_pass, target_username))
    conn.commit()
    conn.close()
    return RedirectResponse("../admin?success=updated", status_code=303)

@app.post("/admin/delete-user", response_class=HTMLResponse)
async def delete_user(request: Request, target_username: str = Form(...)):
    username = request.session.get("username")
    if not username or not request.session.get("is_admin"):
        return RedirectResponse("/", status_code=303)
    
    if target_username == "admin":
        return RedirectResponse("../admin?error=cannot_delete_admin", status_code=303)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (target_username,))
    conn.commit()
    conn.close()
    return RedirectResponse("../admin?success=deleted", status_code=303)

@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

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
