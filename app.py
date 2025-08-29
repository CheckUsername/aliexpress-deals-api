from flask import Flask, request, jsonify
import requests
import hashlib
import time
import os
from urllib.parse import urlencode

app = Flask(__name__)

# احصل على هذه من environment variables (أضفها في Render أو .env محليًا)
APP_KEY = os.environ.get('APP_KEY')  # App Key من AliExpress Developer Console
APP_SECRET = os.environ.get('APP_SECRET')  # App Secret

API_URL = "http://gw.api.taobao.com/router/rest"

def sign_request(params):
    """توليد التوقيع (sign) باستخدام MD5"""
    if not APP_SECRET:
        raise ValueError("APP_SECRET غير معرف")
    
    # فرز المعلمات أبجديًا
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    sorted_string = ''.join([f"{k}{v}" for k, v in sorted_params])
    
    # إضافة السر قبل وبعد
    bookend_string = APP_SECRET + sorted_string + APP_SECRET
    
    # MD5 hash وتحويل إلى uppercase hex
    sign = hashlib.md5(bookend_string.encode('utf-8')).hexdigest().upper()
    return sign

@app.route("/")
def deal():
    query = request.args.get("query", "wireless earbuds")
    
    if not APP_KEY or not APP_SECRET:
        return jsonify({"error": "APP_KEY أو APP_SECRET غير معرف"}), 500
    
    # المعلمات الأساسية
    params = {
        "method": "aliexpress.affiliate.product.query",  # للبحث بكلمات مفتاحية
        "app_key": APP_KEY,
        "sign_method": "md5",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),  # UTC time
        "format": "json",
        "v": "2.0",
        "keywords": query,  # الكلمات المفتاحية
        "page_no": "1",
        "page_size": "1",  # نأخذ منتج واحد فقط
        "target_currency": "USD",
        "target_language": "EN",  # أو AR للعربية إذا دعم
        # أضف tracking_id إذا كان لديك: "tracking_id": "slotxo24"
    }
    
    # توليد التوقيع وإضافته
    params["sign"] = sign_request(params)
    
    # إرسال الطلب كـ POST (مطلوب لـ API)
    try:
        response = requests.post(API_URL, data=params)
        if response.status_code != 200:
            return jsonify({"error": "API unavailable", "status": response.status_code}), response.status_code
        
        data = response.json()
        
        # التحقق من وجود خطأ في الرد
        if "error_response" in data:
            return jsonify({"error": data["error_response"]})
        
        # استخراج النتائج (من resp_result.resp_detail_infos)
        products = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        if not products:
            return jsonify({"error": "No products found"})
        
        product = products[0]  # الأول
        
        # استخراج الحقول المطلوبة
        result = {
            "title": product.get("subject"),  # عنوان المنتج
            "price_after_coupon": product.get("discount_price"),  # سعر بعد التخفيض (قد يكون discount_price أو target_sale_price)
            "promo_code": product.get("promotion_code"),  # كود ترويجي إذا متوفر (قد لا يكون مباشرًا؛ تحقق في الرد)
            "affiliate_link": product.get("promotion_link")  # رابط الإحالة
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/callback")
def callback():
    # إذا كنت تستخدم OAuth، أضف هنا التعامل مع code، لكن حاليًا فقط OK
    code = request.args.get('code')
    if code:
        # مثال: احفظ أو تبادل بـ access_token (أضف كود إذا لزم)
        return jsonify({"message": "Callback received", "code": code}), 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
