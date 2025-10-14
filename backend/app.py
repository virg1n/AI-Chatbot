import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS

from backend.embedding import (
    create_index,
    embed_text,
    ingest_image_file,
)
from backend.faiss_index import DEFAULT_IMAGES_DIR

app = Flask(__name__)
CORS(app, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000"
])

MINIMUM_SCORE = 0.25

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB upload cap
os.makedirs(DEFAULT_IMAGES_DIR, exist_ok=True)

# Load / initialize the index & model once
index = create_index()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "vectors": index.count(),
    })


@app.route("/search", methods=["POST"])
def search():
    """
    Body: { "prompt": "a red car on the street", "top_k": 5 }
    Returns: { "results": [ { "id": ..., "path": ..., "score": ... }, ... ] }
    """
    
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get("prompt", "").strip()
    print(prompt)
    top_k = int(data.get("top_k", 5))
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    if top_k <= 0:
        top_k = 5

    try:
        q = embed_text(prompt)
        results = index.search(q, top_k=top_k)
        out = []
        maximum_score = {"id": 0, "path": 0, "score": -9999}
        for ext_id, path, score in results:
            print(score)
            if score >= MINIMUM_SCORE:
                out.append({"id": ext_id, "path": path, "score": score})
            if score > maximum_score["score"]:
                maximum_score = {"id": ext_id, "path": path, "score": score}
        
        if len(out) == 0:
            out.append(maximum_score)

        return jsonify({"results": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ingest-image", methods=["POST"])
def ingest_image():
    """
    Multipart form-data:
      - image: file
    Returns: { "id": ..., "path": ... }
    """
    if "image" not in request.files:
        return jsonify({"error": "image file is required (multipart/form-data)"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    try:
        ext_id, path = ingest_image_file(
            index=index,
            image_file=file.stream,
            filename_hint=secure_filename(file.filename),
        )
        return jsonify({"id": ext_id, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True, use_reloader=False)
