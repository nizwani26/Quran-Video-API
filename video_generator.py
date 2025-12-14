import moviepy.editor as mp
from moviepy.editor import TextClip
import os
import requests
from PIL import Image, ImageDraw, ImageFont
import argparse
import sys

# --- الثوابت والإعدادات ---
# المسارات يجب أن تكون ثابتة ليعمل الكود في بيئة سحابية
OUTPUT_DIR = "output"
# نستخدم المسار المطلق لضمان العثور على الخط في أي بيئة
FONT_ARABIC = os.path.abspath("font.ttf") 

# إعدادات الفيديو الأساسية
W, H = 1080, 1920  # دقة الفيديو (للهواتف الذكية/القصص)
TEXT_COLOR = 'white'
FONT_SIZE = 80
BG_IMAGE_PATH = "background.jpg" # تأكد من وجود صورة خلفية في نفس المجلد
TARGET_FPS = 30
# -------------------------

def generate_video(ayah_text: str, reciter_audio_url: str, output_filename="final_video.mp4"):
    """
    يقوم بتوليد فيديو من النص، ويحمّل الصوت من رابط URL.
    
    :param ayah_text: نص الآية المراد عرضها.
    :param reciter_audio_url: رابط URL لملف الصوت MP3.
    :param output_filename: اسم ملف الإخراج.
    :return: المسار الكامل لملف الفيديو النهائي.
    """
    
    # 1. التأكد من وجود مجلد الإخراج
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 2. تحميل ملف الصوت من URL
    audio_temp_path = os.path.join(OUTPUT_DIR, f"audio_{os.getpid()}.mp3")
    print(f"-> Downloading audio from: {reciter_audio_url}")
    
    try:
        response = requests.get(reciter_audio_url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(audio_temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            raise Exception(f"Failed to download audio. Status code: {response.status_code}")
    except requests.exceptions.Timeout:
        raise Exception("Audio download timed out.")
    except Exception as e:
        raise Exception(f"Error during audio download: {e}")

    # 3. تحميل الصوت لتحديد مدة الفيديو
    audio_clip = mp.AudioFileClip(audio_temp_path)
    video_duration = audio_clip.duration

    # 4. تجهيز مقطع النص (TextClip)
    # نستخدم encoding='utf-8' لضمان دعم اللغة العربية
    txt_clip = TextClip(
        ayah_text, 
        fontsize=FONT_SIZE, 
        color=TEXT_COLOR, 
        font=FONT_ARABIC, 
        bg_color='transparent',
        size=(W * 0.9, H * 0.9), # عرض النص 90% من عرض الفيديو
        method='caption', # لضمان التفاف النص
        align='center',
        encoding='utf-8'
    ).set_duration(video_duration)
    
    # وضع النص في منتصف الشاشة
    txt_clip = txt_clip.set_pos('center')

    # 5. تجهيز مقطع الخلفية (Background)
    # نستخدم صورة ثابتة كخلفية
    try:
        if os.path.exists(BG_IMAGE_PATH):
            background_clip = mp.ImageClip(BG_IMAGE_PATH, duration=video_duration)
            # نضمن أن الخلفية بحجم الفيديو المطلوب (1080x1920)
            background_clip = background_clip.resize(newsize=(W, H))
        else:
            # في حال عدم وجود صورة الخلفية، نستخدم خلفية سوداء صلبة
            print("WARNING: Background image not found. Using black background.")
            background_clip = mp.ColorClip(size=(W, H), color=(0,0,0), duration=video_duration)
    except Exception as e:
        print(f"Error loading background: {e}. Using black background.")
        background_clip = mp.ColorClip(size=(W, H), color=(0,0,0), duration=video_duration)


    # 6. دمج الفيديو والصوت والنص
    final_clip = mp.CompositeVideoClip([background_clip, txt_clip.set_opacity(0.8)], size=(W, H))
    
    # إضافة المقطع الصوتي
    final_clip = final_clip.set_audio(audio_clip)

    # 7. كتابة الملف النهائي
    final_video_path = os.path.join(OUTPUT_DIR, output_filename)
    
    print(f"-> Writing final video to: {final_video_path}")
    final_clip.write_videofile(
        final_video_path, 
        codec='libx264', 
        audio_codec='aac', 
        temp_audiofile='temp-audio.m4a', 
        remove_temp=True,
        fps=TARGET_FPS,
        logger=None # لإخفاء بعض رسائل moviepy
    )

    # 8. تنظيف الملفات المؤقتة
    audio_clip.close()
    if os.path.exists(audio_temp_path):
        os.remove(audio_temp_path)
        
    return final_video_path

# ------------------------------------------------------------
# المنطق الرئيسي للتشغيل من سطر الأوامر (مهم لـ GitHub Actions)
# ------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate Quran video from text and audio URL.")
    parser.add_argument('--text', required=True, help='Ayah text content.')
    parser.add_argument('--audio-url', required=True, help='URL to the reciter audio MP3 file.')
    parser.add_argument('--output-name', default="final_video.mp4", help='Output video filename.')
    
    args = parser.parse_args()
    
    try:
        final_video_path = generate_video(
            ayah_text=args.text, 
            reciter_audio_url=args.audio_url,
            output_filename=args.output_name
        )
        # طباعة المسار في النهاية لكي يتمكن GitHub Action من قراءته
        print(f"SUCCESS_OUTPUT_PATH:{final_video_path}")
        sys.exit(0)
        
    except Exception as e:
        print(f"FAILURE_ERROR:{e}", file=sys.stderr)
        sys.exit(1)
