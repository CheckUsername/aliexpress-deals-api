from flask import Flask, request, jsonify
import requests
import hashlib
import time
import os
import re

app = Flask(__name__)

# Environment variables
APP_KEY = os.environ.get('APP_KEY')
APP_SECRET = os.environ.get('APP_SECRET')
TRACKING_ID = os.environ.get('TRACKING_ID')  # Optional, from Affiliate Portal

API_URL = "http://gw.api.taobao.com/router/rest"

def sign_request(params):
    """Generate MD5 signature for AliExpress API"""
    if not APP_SECRET:
        raise ValueError("APP_SECRET is not set")
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    sorted_string = ''.join([f"{k}{v}" for k, v in sorted_params])
    bookend_string = APP_SECRET + sorted_string + APP_SECRET
    return hashlib.md5(bookend_string.encode('utf-8')).hexdigest().upper()

def extract_product_id(url):
    """Extract product_id from AliExpress URL"""
    # Handles both s.click.aliexpress.com and regular URLs like aliexpress.com/item/123.html
    try:
        # First, resolve shortened URLs (s.click.aliexpress.com)
        response = requests.get(url, allow_redirects=True)
        final_url = response.url
        # Extract product_id (e.g., 123 from /item/123.html)
        match = re.search(r'item/(\d+)\.html', final_url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        return None

@app.route("/")
def deal():
    query = request.args.get("query", "https://s.click.aliexpress.com/e/_EG3MC4q")
    
    if not APP_KEY or not APP_SECRET:
        return jsonify({"error": "APP_KEY or APP_SECRET not set"}), 500
    
    # Extract product_id from URL
    product_id = extract_product_id(query)
    if not product_id:
        return jsonify({"error": "Invalid product URL or unable to extract product_id"}), 400
    
    # API parameters for product details
    params = {
        "method": "aliexpress.affiliate.productdetail.get",
        "app_key": APP_KEY,
        "sign_method": "md5",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "format": "json",
        "v": "2.0",
        "product_ids": product_id,
        "target_currency": "USD",
        "target_language": "EN",  # Use AR if Arabic is supported
        "tracking_id": TRACKING_ID if TRACKING_ID else "",
    }
    
    # Generate signature
    try:
        params["sign"] = sign_request(params)
        response = requests.post(API_URL, data=params)
        if response.status_code != 200:
            return jsonify({"error": "API unavailable", "status": response.status_code}), response.status_code
        
        data = response.json()
        
        # Check for API errors
        if "error_response" in data:
            return jsonify({"error": data["error_response"]}), 500
        
        # Extract product details
        product_data = data.get("aliexpress_affiliate_productdetail_get_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        if not product_data:
            return jsonify({"error": "No product found"}), 404
        
        product = product_data[0]
        
        # Generate affiliate links for different discount types (simulated with tracking_id variations)
        base_link = product.get("promotion_link", query)
        discount_links = {
            "coins": f"{base_link}&type=coins",
            "superdeals": f"{base_link}&type=superdeals",
            "limited_offer": f"{base_link}&type=limited",
            "bigsave": f"{base_link}&type=bigsave",
            "bundles": f"{base_link}&type=bundles",
        }
        
        # Response formatted as per your initial request
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
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/callback")
def callback():
    code = request.args.get('code')
    if code:
        return jsonify({"message": "Callback received", "code": code}), 200
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
