# AliExpress Deals API
خدمة سحابية تستخرج معلومات المنتج وروابط التخفيضات من AliExpress باستخدام Affiliate API.

## المميزات
- استخراج عنوان المنتج، عدد المبيعات، والتقييم.
- إنشاء روابط تابعة (affiliate links) لأنواع التخفيضات (عملات، Superdeals، عرض محدود، Bigsave، حزمات).
- النشر على Render.com باستخدام Docker و Gunicorn.

## المتطلبات
- **App Key و App Secret**: احصل عليهما من AliExpress Developer Console (https://developers.aliexpress.com/).
- **Tracking ID**: احصل عليه من Affiliate Portal (https://portals.aliexpress.com/) (اختياري).
- **Python 3.10+** و Docker للتشغيل أو النشر.

## إعداد المتغيرات البيئية
1. أنشئ ملف `.env` محليًا (لا ترفعه إلى GitHub):
