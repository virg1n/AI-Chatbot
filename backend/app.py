import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
from urllib.parse import quote
from backend.faiss_index import DEFAULT_DATA_DIR

from backend.embedding import (
    create_index,
    embed_text,
    ingest_image_file,
)
from backend.faiss_index import DEFAULT_IMAGES_DIR
from backend.people_db import init_db, get_person, create_or_update_person


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

init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "vectors": index.count(),
    })

def file_path_to_url(p: str) -> str:
    """
    /var/www/mindxium/data/images/cat.jpg  ->  /data/images/cat.jpg
    """
    try:
        rel = os.path.relpath(p, DEFAULT_DATA_DIR) 
    except ValueError:
        rel = os.path.basename(p)
    return "/data/" + quote(rel.replace(os.sep, "/"))

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


            # if score >= MINIMUM_SCORE:
            #     out.append({"id": ext_id, "path": file_path_to_url(path), "score": score})
            # if score > maximum_score["score"]:
            #     maximum_score = {"id": ext_id, "path": file_path_to_url(path), "score": score}
        
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

@app.route("/get_info", methods=["GET", "POST"])
def get_info():
    """
    Get person info by phone_number.
    - GET:   /get_info?phone_number=...
    - POST:  JSON { "phone_number": "..." }
    Returns 404 if not found.
    """
    try:
        if request.method == "GET":
            phone = (request.args.get("phone_number") or "").strip()
        else:
            data = request.get_json(force=True, silent=True) or {}
            phone = (data.get("phone_number") or "").strip()

        if not phone:
            return jsonify({"error": "phone_number is required"}), 400

        person = get_person(phone)
        if not person:
            return jsonify({"error": "not found"}), 404

        return jsonify({"person": person})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/set_info", methods=["POST"])
def set_info():
    """
    Create or update a person by phone_number.
    Body JSON must include:
      - phone_number: string (required)
    And may include any of:
      - first_name, last_name, age, relation,
        memory_about, last_conversation, stories_for, questions_for

    Behavior:
      - For appendable fields (memory_about, last_conversation, stories_for, questions_for),
        the new data is APPENDED to whatever exists.
      - For first_name, last_name, relation, age, the value is set/overwritten.
      - If the phone_number doesn't exist, a new person is created.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        phone = (data.get("phone_number") or "").strip()
        if not phone:
            return jsonify({"error": "phone_number is required"}), 400

        # Remove phone_number from payload before passing to updater
        payload = {k: v for k, v in data.items() if k != "phone_number"}

        action, person = create_or_update_person(phone, payload)
        return jsonify({"status": action, "person": person})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run the Flask dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True, use_reloader=False)
