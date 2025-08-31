# استخدام صورة أساسية خفيفة الوزن
FROM python:3.9-slim

# تعيين مجرف العمل
WORKDIR /app

# نسخ ملف المتطلبات أولا للاستفادة من caching في Docker
COPY requirements.txt .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# فتح المنفذ الذي يعمل عليه التطبيق
EXPOSE 10000

# تشغيل التطبيق
CMD ["python", "app.py"]
