import os
import uuid
from typing import List, Tuple, Iterable
import torch
from PIL import Image
import numpy as np
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer

# open-clip-torch is a lightweight CLIP-like local model
import open_clip

from backend.faiss_index import ImageVectorIndex, DEFAULT_IMAGES_DIR

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(DEVICE)
MODEL_NAME = os.environ.get("CLIP_MODEL_NAME", "ViT-B-32")
MODEL_PRETRAINED = os.environ.get("CLIP_PRETRAINED", "openai")  # small & common

_model = None
_preprocess = None
_tokenizer = None
_embed_dim = None

_VITGPT2_MODEL = None
_VITGPT2_EXTRACTOR = None
_VITGPT2_TOKENIZER = None


def get_model():
    global _model, _preprocess, _tokenizer, _embed_dim
    if _model is None:
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=MODEL_PRETRAINED, device=DEVICE
        )
        tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        model.eval()
        _model = model
        _preprocess = preprocess
        _tokenizer = tokenizer
        # infer embed dim
        with torch.no_grad():
            dummy = torch.randn(1, 3, 224, 224, device=DEVICE)
            feat = model.encode_image(dummy)
            _embed_dim = int(feat.shape[-1])
    return _model, _preprocess, _tokenizer, _embed_dim

def _load_vitgpt2_captioner():
    global _VITGPT2_MODEL, _VITGPT2_EXTRACTOR, _VITGPT2_TOKENIZER
    if _VITGPT2_MODEL is None:
        

        model_name = "nlpconnect/vit-gpt2-image-captioning"
        _VITGPT2_MODEL = VisionEncoderDecoderModel.from_pretrained(model_name).to(DEVICE)
        _VITGPT2_MODEL.eval()
        _VITGPT2_EXTRACTOR = ViTImageProcessor.from_pretrained(model_name)
        _VITGPT2_TOKENIZER = AutoTokenizer.from_pretrained(model_name)
    return _VITGPT2_MODEL, _VITGPT2_EXTRACTOR, _VITGPT2_TOKENIZER

def _shorten_caption(text: str, max_words: int = 12) -> str:
    words = text.strip().rstrip(".").split()
    return " ".join(words[:max_words])

@torch.no_grad()
def embed_text(prompt: str) -> np.ndarray:
    model, _, tokenizer, _ = get_model()
    tokens = tokenizer([prompt]).to(DEVICE)
    text_feat = model.encode_text(tokens)
    text_feat = text_feat.float().cpu().numpy()[0]
    return text_feat


@torch.no_grad()
def embed_image_pil(img: Image.Image) -> np.ndarray:
    model, preprocess, _, _ = get_model()
    tensor = preprocess(img).unsqueeze(0).to(DEVICE)
    img_feat = model.encode_image(tensor)
    img_feat = img_feat.float().cpu().numpy()[0]
    return img_feat


def allowed_ext(fname: str) -> bool:
    ext = os.path.splitext(fname.lower())[1]
    return ext in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def ingest_image_file(
    index: ImageVectorIndex,
    image_file,
    filename_hint: str = None,
) -> Tuple[str, str]:
    """
    Save an uploaded image file to disk, embed it, and add to index.
    image_file: a file-like object (e.g., from Flask's request.files['image'])
    Returns (ext_id, saved_path).
    """
    os.makedirs(DEFAULT_IMAGES_DIR, exist_ok=True)
    ext = os.path.splitext(filename_hint or "image.jpg")[1] or ".jpg"
    if ext.lower() not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        ext = ".jpg"

    ext_id = str(uuid.uuid4())
    saved_path = os.path.join(DEFAULT_IMAGES_DIR, f"{ext_id}{ext}")

    # Save file
    with open(saved_path, "wb") as f:
        f.write(image_file.read())

    # Embed
    img = Image.open(saved_path).convert("RGB")
    vec = embed_image_pil(img).astype(np.float32)[None, :]

    # Add to index
    index.add([ext_id], [saved_path], vec)
    return ext_id, saved_path


def build_index_from_folder(
    folder: str,
    index: ImageVectorIndex,
    batch_size: int = 32,
) -> int:
    """
    Walk a folder, embed all images, and append them to the main index.
    Uses randomly generated UUIDs as ext_ids; paths are absolute saved paths (copied into data/images).
    Returns count of newly ingested images.
    """
    assert os.path.isdir(folder), f"Folder not found: {folder}"
    os.makedirs(DEFAULT_IMAGES_DIR, exist_ok=True)

    # Collect image paths
    files = []
    for root, _, fnames in os.walk(folder):
        for fn in fnames:
            if allowed_ext(fn):
                files.append(os.path.join(root, fn))
    files.sort()
    if not files:
        return 0

    model, preprocess, _, _ = get_model()

    ingested = 0
    ext_ids: List[str] = []
    paths: List[str] = []
    vecs: List[np.ndarray] = []

    def flush():
        nonlocal ext_ids, paths, vecs, ingested
        if not vecs:
            return
        arr = np.vstack(vecs).astype(np.float32)
        index.add(ext_ids, paths, arr)
        ingested += len(ext_ids)
        ext_ids, paths, vecs = [], [], []

    with torch.no_grad():
        batch_imgs = []
        batch_meta = []

        for src_path in files:
            try:
                img = Image.open(src_path).convert("RGB")
            except Exception:
                continue

            # Copy image into the central images folder with new UUID to ensure stable ID & path
            ext = os.path.splitext(src_path)[1]
            if ext.lower() not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
                ext = ".jpg"
            ext_id = str(uuid.uuid4())
            dst_path = os.path.join(DEFAULT_IMAGES_DIR, f"{ext_id}{ext}")

            # Save (re-encode) to maintain consistent format
            try:
                img.save(dst_path)
            except Exception:
                # Fallback to PNG
                dst_path = os.path.join(DEFAULT_IMAGES_DIR, f"{ext_id}.png")
                img.save(dst_path)

            batch_imgs.append(preprocess(img))
            batch_meta.append((ext_id, dst_path))

            if len(batch_imgs) == batch_size:
                tensor = torch.stack(batch_imgs).to(DEVICE)
                feats = model.encode_image(tensor).float().cpu().numpy()
                for (eid, pth), vec in zip(batch_meta, feats):
                    ext_ids.append(eid)
                    paths.append(pth)
                    vecs.append(vec)
                batch_imgs, batch_meta = [], []

                if len(vecs) >= 512:  # chunk FAISS writes
                    flush()

        # tail
        if batch_imgs:
            tensor = torch.stack(batch_imgs).to(DEVICE)
            feats = model.encode_image(tensor).float().cpu().numpy()
            for (eid, pth), vec in zip(batch_meta, feats):
                ext_ids.append(eid)
                paths.append(pth)
                vecs.append(vec)

        flush()

    return ingested


def create_index(dim_override: int = None) -> ImageVectorIndex:
    """
    Utility to create an ImageVectorIndex with the correct dimensionality.
    """
    _, _, _, embed_dim = get_model()
    dim = int(dim_override or embed_dim)
    return ImageVectorIndex(dim=dim)

@torch.no_grad()
def generate_short_description(image_path: str, max_new_tokens: int = 20) -> Tuple[str, float]:
    """
    Generate a short, plain-English description for an image.

    Returns:
        (caption, quality_score)
        - caption: short string
        - quality_score: a rough confidence proxy in [0..1] (not used by the endpoint)
    """
    model, extractor, tokenizer = _load_vitgpt2_captioner()

    img = Image.open(image_path).convert("RGB")
    pixel_values = extractor(images=img, return_tensors="pt").pixel_values.to(DEVICE)

    outputs = model.generate(
        pixel_values,
        max_new_tokens=max_new_tokens,
        num_beams=3,
        do_sample=False,
        early_stopping=True,
        no_repeat_ngram_size=2,
    )
    caption = tokenizer.decode(outputs[0], skip_special_tokens=True)
    caption = _shorten_caption(caption, max_words=12)

    # Produce a light-weight "quality" proxy from logit scores if available (fallback to 1.0)
    try:
        # Greedy/beam search doesn't expose probs directly; this is a simple heuristic.
        # You can wire logits processing for a better score if needed.
        quality = 1.0
    except Exception:
        quality = 1.0

    return caption, float(quality)