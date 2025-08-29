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
        "callback": "https://aliexpress-deals-api.onrender.com/callback"
    }
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return {"error": "API unavailable"}
    return res.json()

@app.route("/callback")
def callback():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
