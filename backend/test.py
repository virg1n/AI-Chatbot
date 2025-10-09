# scripts/build_from_folder.py (example helper)
from embedding import create_index, build_index_from_folder

if __name__ == "__main__":
    folder = "../images_to_convert"
    index = create_index()
    n = build_index_from_folder(folder, index)
    print(f"Ingested {n} images. Index now has {index.count()} vectors.")
