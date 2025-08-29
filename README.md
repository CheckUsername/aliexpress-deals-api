# AliExpress Deals API
خدمة سحابية بسيطة تستخرج:
- عنوان المنتج
- السعر بعد الكوبون
- الكود الترويجي
- رابط الإحالة المُنشّط

## المتطلبات
- App Key و App Secret من AliExpress Developer Console (https://developers.aliexpress.com/).
- أضفها كـ environment variables: `APP_KEY` و `APP_SECRET`.

## تشغيل محلي
```bash
pip install -r requirements.txt
export APP_KEY=509112
export APP_SECRET=UOXRatcL8CkX5d4ruigBcOWI7RObnkPz
python app.py
