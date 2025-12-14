import requests
import os
import uuid # نستخدم uuid بدلاً من pid لضمان فرادة الملفات المؤقتة
from moviepy.editor import *
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import sys

# --- الإعدادات والثوابت ---
OUTPUT_DIR = "output"
FONT_ARABIC = "font.ttf" 

# --- الوظائف الأساسية ---

def fetch_ayah_data(ayah_number, reciter_name):
    """يجلب نص الآية ورابط الصوت واسم السورة."""
    
    response_ayah = requests.get(f"http://api.alquran.cloud/v1/ayah/{ayah_number}")
    response_ayah.raise_for_status()
    ayah_data = response_ayah.json()['data']

    reciter_url = f"http://api.alquran.cloud/v1/ayah/{ayah_number}/editions/{reciter_name}"
    response_reciter = requests.get(reciter_url)
    response_reciter.raise_for_status()
    audio_url = response_reciter.json()['data'][0]['audio']
    
    surah_name = ayah_data['surah']['englishName']
    ayah_text = ayah_data['text']
    
    return ayah_text, audio_url, surah_name

def create_image_background(text, surah_name, temp_image_path):
    """ينشئ صورة خلفية بالآية واسم السورة."""
    
    WIDTH, HEIGHT = 1280, 720
    BACKGROUND_COLOR = (0, 0, 0)
    TEXT_COLOR = (255, 255, 255)
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BACKGROUND_COLOR)
    d = ImageDraw.Draw(img)

    font_size = 48
    try:
        font = ImageFont.truetype(FONT_ARABIC, font_size)
    except IOError:
        font = ImageFont.load_default()
        
    lines = []
    words = text.split()
    current_line = ""
    
    # تقسيم النص إلى أسطر (لضمان عمله في البيئة السحابية)
    for word in words:
        temp_line = f"{word} {current_line}".strip()
        text_width = d.textlength(temp_line, font=font)
        
        if text_width < WIDTH - 100:
            current_line = temp_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    lines.reverse()
    
    y_text = (HEIGHT - len(lines) * font_size * 1.5) // 2 
    
    for line in lines:
        line = line[::-1] 
        text_width = d.textlength(line, font=font)
        x_text = (WIDTH - text_width) // 2
        d.text((x_text, y_text), line, fill=TEXT_COLOR, font=font)
        y_text += int(font_size * 1.5)

    surah_text = f"سورة {surah_name}"
    font_small = ImageFont.truetype(FONT_ARABIC, 30) if os.path.exists(FONT_ARABIC) else ImageFont.load_default()
    surah_width = d.textlength(surah_text, font=font_small)
    d.text(((WIDTH - surah_width) // 2, HEIGHT - 50), surah_text, fill=(150, 150, 150), font=font_small)

    img.save(temp_image_path)
    return temp_image_path

def create_video(audio_url, reciter_name, ayah_number, temp_image_path, temp_audio_path):
    """يجلب ملف الصوت، ويحدّد مدته، وينشئ مقطع الفيديو."""
    
    # استخدام UUID لتوليد اسم فريد للفيديو النهائي
    unique_id = uuid.uuid4().hex
    final_video_path = os.path.join(OUTPUT_DIR, f"{reciter_name}_{ayah_number}_{unique_id}.mp4") 
    
    # 1. جلب ملف الصوت مؤقتًا
    audio_response = requests.get(audio_url)
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_response.content)

    # 2. تحديد مدة الصوت
    audio_segment = AudioSegment.from_mp3(temp_audio_path)
    audio_duration = audio_segment.duration_seconds

    # 3. إنشاء المقطع باستخدام moviepy
    image_clip = ImageClip(temp_image_path, duration=audio_duration)
    audio_clip = AudioFileClip(temp_audio_path)
    
    final_clip = image_clip.set_audio(audio_clip)
    
    # 4. كتابة ملف الفيديو النهائي
    final_clip.write_videofile(
        final_video_path,
        codec='libx264', 
        audio_codec='aac', 
        fps=24,
        verbose=False,
        logger=None 
    )
    return final_video_path

def cleanup(paths):
    """حذف الملفات المؤقتة."""
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass 

def generate_full_video(ayah_number, reciter_name):
    """الدالة الرئيسية لتوليد الفيديو لاستخدامها في API."""
    
    # استخدام UUID لإنشاء مسارات مؤقتة فريدة للتجنب التام لأي تعارض
    unique_id = uuid.uuid4().hex
    temp_audio_path = os.path.join(OUTPUT_DIR, f"temp_audio_{unique_id}.mp3")
    temp_image_path = os.path.join(OUTPUT_DIR, f"temp_image_{unique_id}.png")
    
    final_video_path = None
    try:
        # 1. جلب البيانات
        ayah_text, audio_url, surah_name = fetch_ayah_data(ayah_number, reciter_name)

        # 2. إنشاء الصورة
        create_image_background(ayah_text, surah_name, temp_image_path)

        # 3. إنشاء الفيديو
        final_video_path = create_video(audio_url, reciter_name, ayah_number, temp_image_path, temp_audio_path)
        
        return final_video_path
        
    finally:
        # 4. التنظيف التلقائي للملفات المؤقتة
        cleanup([temp_audio_path, temp_image_path])
        