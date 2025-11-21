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
)
from backend.faiss_index import DEFAULT_IMAGES_DIR
from backend.people_db import init_db, get_person, get_person_by_name, create_or_update_person

import random
import numpy as np

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app, origins=[
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:5000"
])

MINIMUM_SCORE = 0.25
HIGH_SCORE_THRESHOLD = 0.6  # used to adapt minimum score per-query

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

def dynamic_minimum_score(scores):
    if not scores:
        return MINIMUM_SCORE
    top = max(scores)
    factor = 0.6 if top >= HIGH_SCORE_THRESHOLD else 0.7
    return max(MINIMUM_SCORE, top * factor)

def combine_score(faiss_score: float, desc_score: float, weight_img: float = 0.8, weight_desc: float = 0.2) -> float:
    return (faiss_score * weight_img) + (desc_score * weight_desc)

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

@app.route("/manage-images")
def manage_images():
    return render_template("manage_images.html")


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
        maximum_score = None

        # normalize query for text-to-text scoring
        qnorm = q / (float((q**2).sum()) ** 0.5 + 1e-12)

        for ext_id, path, score, caption, user_caption, is_active in results:
            web_url = file_path_to_url(path)  # <-- convert to /data/...
            if not is_active:
                continue
            description = user_caption or caption

            # description similarity (text-to-text)
            desc_score = 0.0
            desc_weight = 0.2  # auto/default
            if user_caption:
                desc_weight = 0.35
            if description:
                dvec = embed_text(description)
                dvec /= (float((dvec**2).sum()) ** 0.5 + 1e-12)
                desc_score = float(np.dot(qnorm, dvec))

            combined_score = combine_score(score, desc_score, weight_img=0.8, weight_desc=desc_weight)

            entry = {"id": ext_id, "path": web_url, "score": combined_score, "description": description}
            out.append(entry)
            if (maximum_score is None) or combined_score > maximum_score["score"]:
                maximum_score = entry

        # apply adaptive minimum
        min_score = dynamic_minimum_score([r["score"] for r in out])
        out = [r for r in out if r["score"] >= min_score]

        if not out:
            if maximum_score:
                out.append(maximum_score)
            else:
                return jsonify({"results": []})

        return jsonify({"results": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ingest-image", methods=["POST"])
def ingest_image():
    """
    Multipart form-data:
      - image: file (required)
      - description: optional custom caption to improve recall
    Returns: { "id": ..., "path": ..., "description": ... }
    """
    if "image" not in request.files:
        return jsonify({"error": "image file is required (multipart/form-data)"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    try:
        user_description = (request.form.get("description") or request.form.get("caption") or "").strip()

        ext_id, path, stored_description = ingest_image_file(
            index=index,
            image_file=file.stream,
            filename_hint=secure_filename(file.filename),
            user_description=user_description,
        )
        return jsonify({
            "id": ext_id,
            "path": path,
            "description": stored_description,
            "description_source": "user" if user_description else "auto",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/check_image", methods=["POST"])
def check_image():
    """
    Body: { "query": "image of hong kong" }
    Returns:
      {
        "description": "<best description or null>",
        "descriptions": ["<desc1>", "<desc2>", ...]
      }
      Descriptions correspond to the most relevant images for the query,
      sorted by combined image+text similarity and filtered by dynamic threshold.
    """
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get("query") or "").strip()
    top_k = int(data.get("top_k", 5))
    if not query:
        return jsonify({"error": "query is required"}), 400
    if top_k <= 0:
        top_k = 5

    try:
        # 1) Embed the query and search your image index
        qvec = embed_text(query)
        results = index.search(qvec, top_k=top_k)

        if not results:
            return jsonify({"description": None, "descriptions": []})

        matched = []
        best_any = None

        # normalized query for text-to-text scoring
        qnorm = qvec / (float((qvec**2).sum()) ** 0.5 + 1e-12)

        for ext_id, path, score, caption, user_caption, is_active in results:
            if not is_active:
                continue
            web_url = file_path_to_url(path)
            desc = user_caption or caption

            desc_score = 0.0
            desc_weight = 0.2
            if user_caption:
                desc_weight = 0.35
            if desc:
                dvec = embed_text(desc)
                dvec /= (float((dvec**2).sum()) ** 0.5 + 1e-12)
                desc_score = float(np.dot(qnorm, dvec))

            combined_score = combine_score(score, desc_score, weight_img=0.8, weight_desc=desc_weight)
            entry = {
                "id": ext_id,
                "path": web_url,
                "score": float(combined_score),
                "description": desc,
            }
            matched.append(entry)
            if (best_any is None) or combined_score > best_any["score"]:
                best_any = entry

        if not matched and best_any:
            matched.append(best_any)

        # apply adaptive min score
        min_score = dynamic_minimum_score([m["score"] for m in matched])
        filtered = [m for m in matched if m["score"] >= min_score]

        descriptions = [m["description"] for m in filtered if m.get("description")]
        top_description = descriptions[0] if descriptions else None
        return jsonify({
            "description": top_description,
            "descriptions": descriptions,
        })
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

@app.route("/api/images", methods=["GET"])
def list_images():
    try:
        include_inactive = bool(int(request.args.get("include_inactive", "0")))
        rows = index.list_all(include_inactive=include_inactive)
        out = []
        for ext_id, path, caption, user_caption, is_active in rows:
            out.append({
                "id": ext_id,
                "path": file_path_to_url(path),
                "caption": caption,
                "user_caption": user_caption,
                "description": user_caption or caption,
                "is_active": bool(is_active),
            })
        return jsonify({"images": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/images/<ext_id>", methods=["PATCH", "DELETE"])
def update_image(ext_id):
    try:
        if request.method == "DELETE":
            index.set_active(ext_id, 0)
            # best-effort delete file
            row = index.get_by_ext_id(ext_id)
            if row and row[1]:
                try:
                    os.remove(row[1])
                except Exception:
                    pass
            return jsonify({"status": "deleted"})

        data = request.get_json(force=True, silent=True) or {}
        new_desc = (data.get("description") or "").strip()
        index.set_user_caption(ext_id, new_desc or None)
        return jsonify({"status": "updated", "id": ext_id, "description": new_desc or None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/descriptions", methods=["GET"])
def list_descriptions():
    """
    GET /descriptions
    Returns all image IDs, paths and their effective description (user_caption or caption).
    Optional query param: include_inactive=1 to also include inactive images.
    """
    try:
        include_inactive = bool(int(request.args.get("include_inactive", "0")))
        rows = index.list_all(include_inactive=include_inactive)
        out = []
        for ext_id, path, caption, user_caption, is_active in rows:
            out.append({
                # "id": ext_id,
                # "path": file_path_to_url(path),
                "description": user_caption or caption,
                # "is_active": bool(is_active),
            })
        return jsonify({"descriptions": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run the Flask dev server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True, use_reloader=False)
