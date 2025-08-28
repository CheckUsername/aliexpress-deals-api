from flask import Flask, request, jsonify
import requests, hashlib, time

APP_KEY  = "509112"
APP_SECRET = "UOXRatcL8CkX5d4ruigBcOWI7RObnkPz"

app = Flask(__name__)

@app.route("/")
def deal():
    query = request.args.get("query", "")
    params = {
        "app_key": APP_KEY,
        "method": "aliexpress.affiliate.product.query",
        "keywords": query,
        "page_no": 1,
        "page_size": 1,
        "target_currency": "USD",
        "target_language": "EN",
        "timestamp": str(int(time.time())),
        "v": "2.0",
        "format": "json"
    }
    sorted_str = APP_SECRET + ''.join([k + str(v) for k, v in sorted(params.items())]) + APP_SECRET
    params["sign"] = hashlib.md5(sorted_str.encode()).hexdigest().upper()
    res = requests.get("https://gw.api.taobao.com/router/rest", params=params).json()
    p = res["aliexpress_affiliate_product_query_response"]["resp_result"]["result"]["products"][0]
    return jsonify({
        "title": p["product_title"],
        "image": p["product_main_image_url"],
        "price_after": p["sale_price"],
        "coupon_code": p.get("discount_coupon", {}).get("coupon_code", ""),
        "affiliate_link": p["affiliate_link"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
