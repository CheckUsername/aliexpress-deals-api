from flask import Flask, request, jsonify
import requests
import hashlib
import time
import os
import re
import logging

app = Flask(__name__)

# إعداد التسجيل
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
APP_KEY = os.environ.get('APP_KEY')
APP_SECRET = os.environ.get('APP_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID')

API_URL = "http://gw.api.taobao.com/router/rest"

def sign_request(params):
    """Generate MD5 signature for AliExpress API"""
    if not APP_SECRET:
        logger.error("APP_SECRET is not set")
        raise ValueError("APP_SECRET is not set")
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    sorted_string = ''.join([f"{k}{v}" for k, v in sorted_params])
    bookend_string = APP_SECRET + sorted_string + APP_SECRET
    sign = hashlib.md5(bookend_string.encode('utf-8')).hexdigest().upper()
    logger.debug(f"Generated signature: {sign}")
    return sign

def extract_product_id(url):
    """Extract product_id from AliExpress URL"""
    try:
        # Resolve shortened URLs
        response = requests.get(url, allow_redirects=True, timeout=10)
        final_url = response.url
        logger.debug(f"Resolved URL: {final_url}")
        # Extract product_id (e.g., 123 from /item/123.html)
        match = re.search(r'item/(\d+)\.html', final_url)
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
    query = request.args.get("query", "https://s.click.aliexpress.com/e/_EG3MC4q")
    logger.info(f"Received query: {query}")
    
    if not APP_KEY or not APP_SECRET:
        logger.error("APP_KEY or APP_SECRET not set")
        return jsonify({"error": "APP_KEY or APP_SECRET not set"}), 500
    
    # Extract product_id
    product_id = extract_product_id(query)
    if not product_id:
        logger.error("Invalid product URL or unable to extract product_id")
        return jsonify({"error": "Invalid product URL or unable to extract product_id"}), 400
    
    # API parameters
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
        "tracking_id": TRACKING_ID if TRACKING_ID else "",
    }
    
    # Generate signature and send request
    try:
        params["sign"] = sign_request(params)
        logger.debug(f"API request params: {params}")
        response = requests.post(API_URL, data=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"API response: {data}")
        
        # Check for API errors
        if "error_response" in data:
            logger.error(f"API error: {data['error_response']}")
            return jsonify({"error": data["error_response"]}), 500
        
        # Extract product details
        product_data = data.get("aliexpress_affiliate_productdetail_get_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        if not product_data:
            logger.error("No product found in API response")
            return jsonify({"error": "No product found"}), 404
        
        product = product_data[0]
        
        # Generate affiliate links for different discount types
        base_link = product.get("promotion_link", query)
        discount_links = {
            "coins": f"{base_link}&type=coins",
            "superdeals": f"{base_link}&type=superdeals",
            "limited_offer": f"{base_link}&type=limited",
            "bigsave": f"{base_link}&type=bigsave",
            "bundles": f"{base_link}&type=bundles",
        }
        
        # Response
        result = {
            "message": "🛍️ معلومات عن المنتج مع روابط التخفيضات 🛍️",
            "note": "⚠️ ملاحظة مهمة: السعر التخفيض بالعملات في بعض الأحيان غير مضبوط، تأكد من السعر النهائي في صفحة الدفع.",
            "sales_count": product.get("sale_orders", "غير متوفر"),
            "rating": product.get("average_star", "غير متوفر"),
            "discount_links": [
                {"type": "تخفيض بالعملات", "link": discount_links["coins"]},
                {"type": "عرض سوبر ديل", "link": discount_links["superdeals"]},
                {"type": "عرض محدود", "link": discount_links["limited_offer"]},
                {"type": "تخفيض بيج سيف", "link": discount_links["bigsave"]},
                {"type": "عرض الحزمات", "link": discount_links["bundles"]},
            ]
        }
        
        logger.info("Returning successful response")
        return jsonify(result)
    
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return jsonify({"error": f"API request failed: {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/callback")
def callback():
    code = request.args.get('code')
    logger.info(f"Callback received with code: {code}")
    if code:
        return jsonify({"message": "Callback received", "code": code}), 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
