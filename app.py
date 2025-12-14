from flask import Flask, request, jsonify, send_file
import video_generator
import os
import requests.exceptions

app = Flask(__name__)

# المجلد الذي سيتم حفظ الفيديوهات المؤقتة فيه
video_generator.os.makedirs(video_generator.OUTPUT_DIR, exist_ok=True)

@app.route('/generate_video', methods=['GET'])
def generate_video_api():
    """نقطة نهاية API لتوليد الفيديو. تستقبل رقم الآية واسم القارئ."""
    
    # 1. استلام المدخلات
    ayah_number = request.args.get('ayah_number')
    reciter_name = request.args.get('reciter_name', 'maher_almuaiqly') 

    if not ayah_number or not ayah_number.isdigit():
        return jsonify({"error": "الرجاء تحديد رقم آية صحيح (ayah_number)"}), 400

    final_video_path = None
    try:
        # 2. استدعاء الدالة الرئيسية لتوليد الفيديو
        final_video_path = video_generator.generate_full_video(ayah_number, reciter_name)
        
        # 3. إرجاع الملف مباشرة للتحميل
        # استخدام os.path.basename لتحديد اسم الملف في الرأس (Header)
        return send_file(
            final_video_path, 
            as_attachment=True, 
            download_name=os.path.basename(final_video_path), 
            mimetype='video/mp4'
        )

    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"خطأ في جلب البيانات من API: {e.response.status_code}. قد يكون رقم الآية خاطئًا."}), 500
    except Exception as e:
        # خطأ داخلي (قد يكون بسبب moviepy أو FFmpeg إذا لم يتم تثبيتهما بشكل صحيح في الدوكر)
        return jsonify({"error": f"خطأ داخلي في الخادم: {str(e)}"}), 500
    finally:
        # التأكد من حذف الملف النهائي بعد إرساله
        if final_video_path and os.path.exists(final_video_path):
            video_generator.cleanup([final_video_path])


if __name__ == '__main__':
    # لتشغيل الخادم، يجب أن يعمل هذا على المنفذ 5000 داخل الدوكر
    app.run(host='0.0.0.0', port=5000, debug=False)
    