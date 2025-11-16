from flask import Flask, jsonify, request

app = Flask(__name__)

@app.get("/")
def home():
    return "<h1>Hello from Flask 👋</h1><p>Try /hello/YourName or /api/ping</p>"

@app.get("/hello/<name>")
def hello(name):
    return f"Hello, {name}!"

@app.get("/api/ping")
def ping():
    return jsonify(ok=True, message="pong")

@app.post("/api/echo")
def echo():
    data = request.get_json(silent=True) or {}
    return jsonify(received=data), 201

if __name__ == "__main__":
    # dev server: accessible on your LAN
    app.run(host="0.0.0.0", port=8000, debug=True)