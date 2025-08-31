from flask import Flask, request, jsonify
import requests
import hashlib
import time
import os
import re
import logging
from urllib.parse import urlencode
from datetime import datetime

app = Flask(__name__)

# إعداد التسجيل
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
APP_KEY = os.environ.get('APP_KEY')
APP_SECRET = os.environ.get('APP_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID', 'slotxo24')

API_URL = "https://gw.api.taobao.com/router/rest"

def sign_request(params):
    """Generate MD5 signature for AliExpress API according to official docs"""
    if not APP_SECRET:
        logger.error("APP_SECRET is not set")
        raise ValueError("APP_SECRET is not set")
    
    # 1. Sort parameters alphabetically by their key
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    
    # 2. Create a query string with 'key=value' joined by '&'
    sorted_query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    # 3. Prepend and append the APP_SECRET
    bookend_string = APP_SECRET + sorted_query_string + APP_SECRET
    logger.debug(f"String to sign: {bookend_string}")
    
    # 4. Generate MD5 hash and convert to uppercase
    sign = hashlib.md5(bookend_string.encode('utf-8')).hexdigest().upper()
    logger.debug(f"Generated signature: {sign}")
    return sign

def extract_product_id(url):
    """Extract product_id from AliExpress URL"""
    try:
        # إذا كان الرابط مباشرًا يحتوي على product_id
        direct_match = re.search(r'/(\d+)\.html', url)
        if direct_match:
            product_id = direct_match.group(1)
            logger.debug(f"Direct extracted product_id: {product_id}")
            return product_id
        
        # إذا كان رابطًا قصيرًا، نحتاج إلى حل التوجيه
        response = requests.get(url, allow_redirects=True, timeout=10)
        final_url = response.url
        logger.debug(f"Resolved URL: {final_url}")
        
        match = re.search(r'/(\d+)\.html', final_url)
        if match:
            product_id = match.group(1)
            logger.debug(f"Extracted product_id: {product_id}")
            return product_id
        
        logger.error(f"No product_id found in URL: {final_url}")
        return None
    except requests.RequestException as e:
        logger.error(f"Error resolving URL {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting product_id from {url}: {str(e)}")
        return None

@app.route("/")
def deal():
    query = request.args.get("query", "").strip()
    logger.info(f"Received query: {query}")
    
    if not query:
        return jsonify({
            "error": "Query parameter is required",
            "help": "Add ?query=product_name or ?query=product_url to your request"
        }), 400
    
    if not APP_KEY or not APP_SECRET:
        logger.error("APP_KEY or APP_SECRET not set")
        return jsonify({
            "error": "Configuration error: Please set APP_KEY and APP_SECRET in environment variables.",
            "help": "Visit https://developers.aliexpress.com/ to get valid App Key and Secret."
        }), 500
    
    # تحديد ما إذا كان الاستعلام عبارة عن رابط أو اسم منتج
    if query.startswith(('http://', 'https://', 'www.', 'aliexpress.com', 's.click.aliexpress.com')):
        # استخراج product_id من الرابط
        product_id = extract_product_id(query)
        if not product_id:
            return jsonify({
                "error": "Invalid product URL or unable to extract product_id.",
                "help": "Use a valid AliExpress product link"
            }), 400
    else:
        # البحث بالاسم - نستخدم الاستعلام مباشرة
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
        logger.debug(f"API request params: {params}")
        
        # استخدام اتصال مباشر مع timeout مناسب
        response = requests.post(API_URL, data=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"API response: {data}")
        
        if "error_response" in data:
            error_msg = data["error_response"]
            logger.error(f"API error: {error_msg}")
            return jsonify({
                "error": f"API error: {error_msg.get('msg', 'Unknown error')}",
                "details": error_msg,
                "help": "Verify APP_KEY and APP_SECRET in AliExpress Developer Console."
            }), 500
        
        product_data = data.get("aliexpress_affiliate_productdetail_get_response", {})
        product_data = product_data.get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        
        if not product_data:
            logger.error("No product found in API response")
            return jsonify({"error": "No product found for the given query."}), 404
        
        product = product_data[0] if isinstance(product_data, list) else product_data
        
        # استخراج البيانات المطلوبة للواجهة الأمامية
        base_link = product.get("promotion_link", "")
        product_url = product.get("product_url", "")
        
        # معالجة البيانات للواجهة الأمامية
        result = {
            "title": product.get("subject", "غير متوفر"),
            "image_url": product.get("main_image", ""),
            "original_price": product.get("original_price", ""),
            "price_after": product.get("target_sale_price", ""),
            "coupon_code": product.get("promotion_code", "لا يتطلب كوبون"),
            "affiliate_link": base_link,
            "product_url": product_url,
            "discount": product.get("discount", ""),
            "rating": product.get("evaluate_rate", "غير متوفر"),
            "orders": product.get("lastest_volume", "غير متوفر"),
            "shipping": "شحن مجاني" if product.get("free_shipping", False) else "رسوم شحن",
            "store_name": product.get("store_name", "غير متوفر"),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Returning successful response")
        return jsonify(result)
    
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        logger.error(f"Permanent connection failure to API: {str(e)}")
        return jsonify({
            "error": "Cannot connect to the product information service.",
            "help": "This might be a temporary issue with the AliExpress API. Please try again later.",
            "details": str(e)
        }), 503
    
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return jsonify({
            "error": f"API request failed: {str(e)}",
            "help": "Check network connectivity or try again later."
        }), 500
    
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({
            "error": f"Server error: {str(e)}",
            "help": "Contact support or check server logs."
        }), 500

@app.route("/health")
def health_check():
    """Endpoint for health checks"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=os.environ.get("DEBUG", False))
