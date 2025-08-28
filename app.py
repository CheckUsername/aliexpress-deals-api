from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def deal():
    query = request.args.get("query", "wireless earbuds")
    url = "https://portals.aliexpress.com/affiliate/product/search"
    params = {
        "keywords": query,
        "page": 1,
        "size": 1,
        "currency": "USD",
        "lang": "en",
        "affiliate_id": "YOUR_AFFILIATE_ID"  # استبدله بـ ID حسابك
    }
    res = requests.get(url, params=params).json()
    p = res["products"][0]
    return jsonify({
        "title": p["product_title"],
        "image": p["product_image"],
        "price_after": p["sale_price"],
        "coupon_code": p.get("coupon_code", ""),
        "affiliate_link": p["affiliate_link"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
