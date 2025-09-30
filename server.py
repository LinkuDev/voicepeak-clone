from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
import asyncio
from voicepeak_wrapper.voicepeak import Voicepeak, Narrator

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_BASE = os.path.join(BASE_DIR, "output_web")

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Helper: get narrator/emotion list
async def get_narrators():
    client = Voicepeak()
    return await client.get_narrator_list()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    narrators = await get_narrators()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "narrators": narrators,
        "output_base": OUTPUT_BASE
    })

@app.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    narrator_name: str = Form(...),
    emotion: str = Form(...),
    output_folder: str = Form(...),
    text_content: str = Form(""),
    text_file: UploadFile = File(None)
):
    # Tạo thư mục lưu nếu chưa có
    output_path = os.path.join(OUTPUT_BASE, output_folder)
    os.makedirs(output_path, exist_ok=True)

    # Lấy nội dung text
    if text_file:
        file_path = os.path.join(output_path, text_file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(text_file.file, f)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    else:
        lines = [line.strip() for line in text_content.splitlines() if line.strip()]

    # Chuẩn bị client, narrator, emotion
    client = Voicepeak()
    narrator = narrator_name
    emotions = {emotion: 100} if emotion else None

    # Tạo file tổng hợp
    output_txt_path = os.path.join(output_path, "voice_lines.txt")
    with open(output_txt_path, "w", encoding="utf-8") as txt_out:
        for idx, line in enumerate(lines):
            wav_path = os.path.join(output_path, f"voice_{idx}.wav")
            txt_path = os.path.join(output_path, f"text_{idx:02d}.txt")
            txt_out.write(f"{idx}: {line}\n")
            with open(txt_path, "w", encoding="utf-8") as single_txt:
                single_txt.write(line)
            await client.say_text(line, output_path=wav_path, narrator=narrator, emotions=emotions)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "output_path": output_path,
        "lines": lines
    })
