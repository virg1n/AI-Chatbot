import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from flask_cors import CORS
from urllib.parse import quote
from backend.faiss_index import DEFAULT_DATA_DIR
from flask import send_from_directory
from flask import send_file, abort


from backend.embedding import (
    create_index,
    embed_text,
    ingest_image_file,
    generate_short_description,
)
from backend.faiss_index import DEFAULT_IMAGES_DIR
from backend.people_db import init_db, get_person, get_person_by_name, create_or_update_person

import random

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:5000"
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

@app.route("/data/<path:rel>")
def serve_data(rel: str):
    """
    Serve files stored under DEFAULT_DATA_DIR at the /data/* URL.
    Example: /data/images/<uuid>.jpg -> <DEFAULT_DATA_DIR>/images/<uuid>.jpg
    """
    base = os.path.abspath(DEFAULT_DATA_DIR)
    full = os.path.abspath(os.path.join(base, rel))

    # Prevent path traversal and ensure the file exists
    if not full.startswith(base) or not os.path.isfile(full):
        abort(404)

    return send_file(full)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/demo")
def demo():
    return render_template("demo.html")

@app.route("/contact")
def contact():
    return render_template("contact_us.html")

@app.route("/james-kb")
def james_kb():
    return render_template("james-kb.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/add-user")
def add_user():
    return render_template("add_user.html")

@app.route("/upload_image")
def upload():
    return render_template("upload.html")


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
        maximum_score = {"id": 0, "path": "", "score": -9999}

        for ext_id, path, score in results:
            web_url = file_path_to_url(path)  # <-- convert to /data/...
            if score >= MINIMUM_SCORE:
                out.append({"id": ext_id, "path": web_url, "score": score})
            if score > maximum_score["score"]:
                maximum_score = {"id": ext_id, "path": web_url, "score": score}

        if not out:
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

@app.route("/check_image", methods=["POST"])
def check_image():
    """
    Body: { "query": "image of hong kong" }
    Returns:
      { "description": "night cityscape with skyscrapers and harbor" }  if top result score >= MINIMUM_SCORE
      { "description": null }                                           otherwise
    """
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    try:
        # 1) Embed the query and search your image index
        qvec = embed_text(query)
        results = index.search(qvec, top_k=1)

        if not results:
            return jsonify({"description": None})

        ext_id, path, score = results[0]

        # 2) Threshold check
        if float(score) < MINIMUM_SCORE:
            return jsonify({"description": None})

        # 3) "description"
        desc, _ = generate_short_description(path)

        return jsonify({"description": desc})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_info", methods=["GET", "POST"])
def get_info():
    """
    Get person info by phone_number OR by (first_name + last_name).
    - GET:   /get_info?phone_number=...  OR  /get_info?first_name=...&last_name=...
    - POST:  JSON { "phone_number": "..."} OR {"first_name":"...","last_name":"..."}
    Returns 404 if not found.
    """
    try:
        if request.method == "GET":
            phone = (request.args.get("phone_number") or "").strip()
            first_name = (request.args.get("first_name") or "").strip()
            last_name = (request.args.get("last_name") or "").strip()
        else:
            data = request.get_json(force=True, silent=True) or {}
            phone = (data.get("phone_number") or "").strip()
            first_name = (data.get("first_name") or "").strip()
            last_name = (data.get("last_name") or "").strip()

        if phone:
            person = get_person(phone)
        elif first_name and last_name:
            person = get_person_by_name(first_name, last_name)
        else:
            return jsonify({"error": "Provide phone_number OR (first_name and last_name)"}), 400

        if not person:
            return jsonify({"error": "not found"}), 404

        return jsonify({"person": person})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/set_info", methods=["POST"])
def set_info():
    """
    Create or update a person by identifier:
      - phone_number   OR
      - (first_name + last_name)

    Body JSON may include any of:
      - phone_number (string, required if creating a new person)
      - first_name, last_name, age, relation,
        memory_about, last_conversation, stories_for, questions_for

    Behavior:
      - If phone_number is provided: use it to create or update (existing behavior).
      - Else if (first_name + last_name) provided: find the person by name and update.
        If no existing person is found by name, returns 404 (we keep schema minimal).
      - Appendable fields (memory_about, last_conversation, stories_for, questions_for)
        are appended; first_name, last_name, relation, age are overwritten.
    """
    try:
        data = request.get_json(force=True, silent=True) or {}

        phone = (data.get("phone_number") or "").strip()
        first_name = (data.get("first_name") or "").strip()
        last_name = (data.get("last_name") or "").strip()

        # Build payload for update (do not pass phone_number forward)
        payload = {k: v for k, v in data.items() if k != "phone_number"}

        if phone:
            action, person = create_or_update_person(phone, payload)
            return jsonify({"status": action, "person": person})

        # Fallback to name+lastname update
        if first_name and last_name:
            # Find existing by name
            person_lookup = get_person_by_name(first_name, last_name)
            if not person_lookup:
                return jsonify({
                    "error": "not found",
                    "hint": "No existing person with that name. Provide phone_number to create a new person."
                }), 404

            phone_target = person_lookup["phone_number"]
            action, person = create_or_update_person(phone_target, payload)
            return jsonify({"status": action, "person": person})

        return jsonify({"error": "Provide phone_number OR (first_name and last_name)"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_topic_when_silence", methods=["GET"])
def get_topic_when_silence():
    """
    GET /get_topic_when_silence
    Returns: { "topic": "<random topic>" }
    """
    SILENCE_TOPICS = [
    "my new friend from Netherlands",
    "I got a new car BMW",
    ]
    try:
        return jsonify({"topic": random.choice(SILENCE_TOPICS)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True, use_reloader=False)
