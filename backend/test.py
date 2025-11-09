# import random
# import string
# import requests
# from datetime import datetime

# BASE = "https://mindxium.net"

# def rand_chunk(prefix: str) -> str:
#     tail = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
#     return f"{prefix} {tail} @ {datetime.utcnow().isoformat(timespec='seconds')}Z"

# def main():
#     phone = "+4322342"  # fixed for repeatability

#     # First call: create user with minimal fields
#     r = requests.post(
#         f"{BASE}/set_info",
#         json={
#             "phone_number": phone,
#             "first_name": "Bogdan",
#             "last_name": "Da",
#             "relation": "Brother",
#             "memory_about": "He studying at CityU",
#             "stories_for": ["My new cat"],
#         },
#         timeout=10,
#     )
#     print("SET #1:", r.status_code, r.json())

#     # Second call: append more memory + last_conversation
#     # r = requests.post(
#     #     f"{BASE}/set_info",
#     #     json={
#     #         "phone_number": phone,
#     #         "memory_about": rand_chunk("Coffee chat"),
#     #         "last_conversation": rand_chunk("Talked about projects"),
#     #         "age": 28,  # this will overwrite age if present
#     #     },
#     #     timeout=10,
#     # )
#     # print("SET #2:", r.status_code, r.json())

#     # Fetch
#     r = requests.get(f"{BASE}/get_info", params={"phone_number": phone}, timeout=10)
#     print("GET:", r.status_code)
#     print(r.json())

# if __name__ == "__main__":
#     main()


# # # import requests

# # # url = "https://mindxium.net/check_image"
# # # payload = {"query": "my new cat"}

# # # response = requests.post(url, json=payload)

# # # print("Status:", response.status_code)
# # # print("Response:", response.json())


# # import requests

# # url = "https://mindxium.net/check_image"
# # data = {"query": "my cat pet"}

# # response = requests.get(url, json=data)  # Use POST instead of GET

# # if response.ok:
# #     print("Response:", response.json())
# # else:
# #     print(f"Error {response.status_code}: {response.text}")
import os
import random
import string
import requests
from datetime import datetime

BASE = os.environ.get("BASE", "https://mindxium.net") #http://localhost:5000

def rand_chunk(prefix: str) -> str:
    tail = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix} {tail} @ {datetime.utcnow().isoformat(timespec='seconds')}Z"

def main():
    phone = "+77779105577"  # stable for repeatability
    first_name = "Bogdan"
    last_name = "Da"

    # print("1) CREATE by phone_number")
    # r = requests.get(
    #     f"{BASE}/get_topic_when_silence",
    # )
    # print("  ->", r.status_code, r.json())
    # r = requests.post(
    #     f"{BASE}/set_info",
    #     json={
    #         "phone_number": phone,
    #         "first_name": first_name,
    #         "last_name": last_name,
    #         "relation": "Friend",
    #         "age": 45,
    #         "memory_about": "Best friend. We were classmates in unviversity. Now he is doing a business in marketing called as 'Donna marketing'. We talk rarely",
    #         "stories_for": ["My new cat"],
    #         "last_conversation": "Talked about new AI project that related to the AI agents"
    #     },
    #     timeout=10,
    # )
    # print("  ->", r.status_code, r.json())

    # print("\n2) GET by name (first_name+last_name)")
    # r = requests.get(
    #     f"{BASE}/get_info",
    #     params={"first_name": first_name, "last_name": last_name},
    #     timeout=10,
    # )
    # print("  ->", r.status_code, r.json())

    # print("\n3) UPDATE by name (append last_conversation, no phone_number)")
    # r = requests.post(
    #     f"{BASE}/set_info",
    #     json={
    #           "phone_number": phone,
    #             "last_conversation": "Talked about new AI project that related to the AI agents",
    #             "first_name": first_name,
    #             "last_name": last_name
    #     },
    #     timeout=10,
    # )
    # print("  ->", r.status_code, r.json())

    print("\n4) VERIFY by phone_number")
    r = requests.get(f"{BASE}/get_info", params={"first_name": first_name, "last_name":last_name}, timeout=10)
    print("  ->", r.status_code, r.json())

    print("\n5) NEGATIVE: UPDATE by unknown name (expect 404)")
    r = requests.post(
        f"{BASE}/set_info",
        json={
            "first_name": "Unknown",
            "last_name": "Person",
            "memory_about": "Should not create without phone_number"
        },
        timeout=10,
    )
    print("  ->", r.status_code, r.json())

    print("\n6) CHECK /check_image still works (use POST)")
    r = requests.post(f"{BASE}/check_image", json={"query": "my cat pet"}, timeout=10)
    print("  ->", r.status_code, r.json())

if __name__ == "__main__":
    main()
