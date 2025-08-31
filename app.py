from flask import Flask, request, jsonify
import requests
import hashlib
import time
import os
import re
import logging
from datetime import datetime

app = Flask(__name__)

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
APP_KEY = os.environ.get('APP_KEY')
APP_SECRET = os.environ.get('APP_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID', 'slotxo24')

API_URL = "https://gw.api.taobao.com/router/rest"

def sign_request(params):
    """Generate MD5 signature for AliExpress API"""
    if not APP_SECRET:
        logger.error("APP_SECRET is not set")
        raise ValueError("APP_SECRET is not set")
    
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    sorted_query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    bookend_string = APP_SECRET + sorted_query_string + APP_SECRET
    sign = hashlib.md5(bookend_string.encode('utf-8')).hexdigest().upper()
    return sign

def extract_product_id(url):
    """Extract product_id from AliExpress URL"""
    try:
        direct_match = re.search(r'/(\d+)\.html', url)
        if direct_match:
            return direct_match.group(1)
        
        response = requests.get(url, allow_redirects=True, timeout=10)
        final_url = response.url
        
        match = re.search(r'/(\d+)\.html', final_url)
        if match:
            return match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting product_id: {str(e)}")
        return None

@app.route("/")
def home():
    return jsonify({
        "message": "مرحبًا بك في AliExpress Deals API",
        "usage": "استخدم /deal?query=رابط_المنتج أو /deal?query=اسم_المنتج",
        "example": "مثال: /deal?query=https://s.click.aliexpress.com/e/EXAMPLE"
    })

@app.route("/deal")
def deal():
    query = request.args.get("query", "").strip()
    
    if not query:
        return jsonify({
            "error": "معامل query مطلوب",
            "help": "أضف ?query=اسم_المنتج أو ?query=رابط_المنتج إلى الطلب"
        }), 400
    
    if not APP_KEY or not APP_SECRET:
        return jsonify({
            "error": "خطأ في الإعدادات: يرجى تعيين APP_KEY و APP_SECRET"
        }), 500
    
    if query.startswith(('http://', 'https://', 'www.', 'aliexpress.com', 's.click.aliexpress.com')):
        product_id = extract_product_id(query)
        if not product_id:
            return jsonify({
                "error": "رابط منتج غير صالح أو تعذر استخراج product_id."
            }), 400
    else:
        product_id = query
    
    params = {
        "method": "aliexpress.affiliate.productdetail.get",
        "app_key": APP_KEY,
        "sign_method": "md5",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "format": "json",
        "v": "2.0",
        "product_ids": product_id,
        "target_currency": "USD",
        "target_language": "EN",
        "tracking_id": TRACKING_ID,
    }
    
    try:
        params["sign"] = sign_request(params)
        response = requests.post(API_URL, data=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if "error_response" in data:
            error_msg = data["error_response"]
            return jsonify({
                "error": f"خطأ في API: {error_msg.get('msg', 'خطأ غير معروف')}",
                "details": error_msg
            }), 500
        
        product_data = data.get("aliexpress_affiliate_productdetail_get_response", {})
        product_data = product_data.get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        
        if not product_data:
            return jsonify({"error": "لم يتم العثور على منتج لـ query المحدد."}), 404
        
        product = product_data[0] if isinstance(product_data, list) else product_data
        
        result = {
            "title": product.get("subject", "غير متوفر"),
            "image_url": product.get("main_image", ""),
            "original_price": product.get("original_price", ""),
            "price_after": product.get("target_sale_price", ""),
            "coupon_code": product.get("promotion_code", "لا يتطلب كوبون"),
            "affiliate_link": product.get("promotion_link", ""),
            "product_url": product.get("product_url", ""),
            "discount": product.get("discount", ""),
            "rating": product.get("evaluate_rate", "غير متوفر"),
            "orders": product.get("lastest_volume", "غير متوفر"),
            "shipping": "شحن مجاني" if product.get("free_shipping", False) else "رسوم شحن",
            "store_name": product.get("store_name", "غير متوفر"),
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(result)
    
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        return jsonify({
            "error": "لا يمكن الاتصال بخدمة معلومات المنتج.",
            "help": "قد تكون هذه مشكلة مؤقتة مع AliExpress API. يرجى المحاولة مرة أخرى لاحقًا."
        }), 503
    
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            "error": f"خطأ في الخادم: {str(e)}"
        }), 500

@app.route("/callback", methods=['GET', 'POST'])
def callback():
    try:
        if request.method == 'GET':
            params = request.args.to_dict()
            if 'code' in params:
                return jsonify({
                    "code": 0,
                    "msg": "success",
                    "verified": True
                }), 200
            else:
                return jsonify({
                    "code": 0,
                    "msg": "success",
                    "message": "Callback verification endpoint is active"
                }), 200
        
        elif request.method == 'POST':
            data = request.get_json()
            logger.info(f"Callback data received: {data}")
            
            # معالجة بيانات callback هنا حسب احتياجاتك
            # يمكنك حفظها في قاعدة بيانات أو إرسال إشعارات etc.
            
            return jsonify({
                "code": 0,
                "msg": "success",
                "received": True
            }), 200
            
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return jsonify({
            "code": 500,
            "msg": "error",
            "error": str(e)
        }), 500

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "service": "AliExpress Deals API"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
