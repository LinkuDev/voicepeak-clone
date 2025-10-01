from voicepeak_wrapper.util import say_text_sync

from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
import os
import asyncio
import glob
import wave
from pydub import AudioSegment
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
    wav_path = os.path.join(user_dir, f"{index:02d}.wav")
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

@router.post("/api/merge-audio")
async def merge_audio(
    request: Request,
    username: str = Form(...),
    time_key: str = Form(...)
):
    """
    Nối tất cả các file wav đã tạo thành full.wav và tạo file full.srt
    """
    if not username or not time_key:
        return JSONResponse({"error": "Thiếu thông tin."}, status_code=400)
    
    user_dir = os.path.join(STATIC_DIR, username, time_key)
    if not os.path.exists(user_dir):
        return JSONResponse({"error": "Thư mục không tồn tại."}, status_code=404)
    
    # Lấy danh sách file wav và txt theo thứ tự
    wav_files = sorted(glob.glob(os.path.join(user_dir, "[0-9][0-9].wav")))
    txt_files = sorted(glob.glob(os.path.join(user_dir, "[0-9][0-9].txt")))
    
    if not wav_files or not txt_files:
        return JSONResponse({"error": "Không tìm thấy file wav hoặc txt."}, status_code=404)
    
    try:
        # Nối các file wav với khoảng nghỉ 0.5s
        pause_duration = 500  # milliseconds
        pause = AudioSegment.silent(duration=pause_duration)
        
        combined = AudioSegment.empty()
        srt_entries = []
        current_time = 0  # milliseconds
        
        for idx, (wav_file, txt_file) in enumerate(zip(wav_files, txt_files), start=1):
            # Đọc nội dung text
            with open(txt_file, "r", encoding="utf-8") as f:
                text_content = f.read().strip()
            
            # Đọc file wav
            audio = AudioSegment.from_wav(wav_file)
            duration = len(audio)  # milliseconds
            
            # Tạo entry cho SRT
            start_time = current_time
            end_time = current_time + duration
            
            srt_entries.append({
                "index": idx,
                "start": start_time,
                "end": end_time,
                "text": text_content
            })
            
            # Thêm audio vào combined
            combined += audio
            current_time += duration
            
            # Thêm khoảng nghỉ (trừ file cuối cùng)
            if idx < len(wav_files):
                combined += pause
                current_time += pause_duration
        
        # Lưu file full.wav
        full_wav_path = os.path.join(user_dir, "full.wav")
        combined.export(full_wav_path, format="wav")
        
        # Tạo file full.srt
        full_srt_path = os.path.join(user_dir, "full.srt")
        with open(full_srt_path, "w", encoding="utf-8") as srt_file:
            for entry in srt_entries:
                # Format thời gian theo chuẩn SRT: HH:MM:SS,mmm
                start_str = format_srt_time(entry["start"])
                end_str = format_srt_time(entry["end"])
                
                srt_file.write(f"{entry['index']}\n")
                srt_file.write(f"{start_str} --> {end_str}\n")
                srt_file.write(f"{entry['text']}\n\n")
        
        return JSONResponse({
            "full_wav_url": f"/static/{username}/{time_key}/full.wav",
            "full_srt_url": f"/static/{username}/{time_key}/full.srt",
            "total_lines": len(srt_entries),
            "total_duration_seconds": current_time / 1000
        })
    
    except Exception as e:
        error_log = os.path.join(user_dir, "error.log")
        with open(error_log, "a", encoding="utf-8") as err_file:
            err_file.write(f"Lỗi khi merge audio: {str(e)}\n")
        return JSONResponse({"error": str(e)}, status_code=500)


def format_srt_time(milliseconds):
    """
    Chuyển milliseconds thành format SRT: HH:MM:SS,mmm
    """
    seconds = milliseconds / 1000
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(milliseconds % 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
