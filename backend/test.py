# test_info.py
import random
import string
import requests
from datetime import datetime

BASE = "http://localhost:5000"

def rand_chunk(prefix: str) -> str:
    tail = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix} {tail} @ {datetime.utcnow().isoformat(timespec='seconds')}Z"

def main():
    phone = "+15551234567"  # fixed for repeatability

    # # First call: create user with minimal fields
    # r = requests.post(
    #     f"{BASE}/set_info",
    #     json={
    #         "phone_number": phone,
    #         "first_name": "Ada",
    #         "last_name": "Lovelace",
    #         "relation": "friend",
    #         "memory_about": rand_chunk("Met at conference"),
    #         "stories_for": [rand_chunk("Story idea 1"), rand_chunk("Story idea 2")],
    #     },
    #     timeout=10,
    # )
    # print("SET #1:", r.status_code, r.json())

    # # Second call: append more memory + last_conversation
    # r = requests.post(
    #     f"{BASE}/set_info",
    #     json={
    #         "phone_number": phone,
    #         "memory_about": rand_chunk("Coffee chat"),
    #         "last_conversation": rand_chunk("Talked about projects"),
    #         "age": 28,  # this will overwrite age if present
    #     },
    #     timeout=10,
    # )
    # print("SET #2:", r.status_code, r.json())

    # Fetch
    r = requests.get(f"{BASE}/get_info", params={"phone_number": phone}, timeout=10)
    print("GET:", r.status_code)
    print(r.json())

if __name__ == "__main__":
    main()
