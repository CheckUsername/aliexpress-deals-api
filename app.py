from flask import Flask, request, jsonify, render_template_string
import requests

app = Flask(__name__)

# دالة استخراج المنتج عبر AliExpress Portals
def get_product(query):
    url = "https://portals.aliexpress.com/affiliate/product/search"
    params = {
        "keywords": query,
        "page": 1,
        "size": 1,
        "currency": "USD",
        "lang": "en"
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code != 200:
            return {"error": "API unavailable"}
        data = res.json()
        if not data.get("products"):
            return {"error": "No products found"}
        p = data["products"][0]
        return {
            "title": p["product_title"],
            "image": p["product_image"],
            "price_after": p["sale_price"],
            "coupon_code": p.get("coupon_code", ""),
            "affiliate_link": p["affiliate_link"]
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def deal():
    query = request.args.get("query", "wireless earbuds")
    return jsonify(get_product(query))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
