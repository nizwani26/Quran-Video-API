# استخدم صورة Python أساسية
FROM python:3.10-slim

# تحديث النظام وتثبيت FFmpeg الضروري لـ moviepy
# تثبيت ffmpeg يحل مشكلة الاعتماديات على مستوى النظام
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# تعيين دليل العمل (مجلد المشروع)
WORKDIR /app

# نسخ ملف المتطلبات وتثبيت مكتبات Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات الكود الأخرى
COPY . .

# تحديد نقطة الدخول (تشغيل الخادم)
CMD ["python", "app.py"]
