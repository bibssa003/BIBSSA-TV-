import requests
import urllib3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# تعطيل تحذيرات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="BIBSSA TV API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# بيانات سيرفر Xtream الخاصة بك
XTREAM_URL = "http://milo2080.com:80"
USERNAME = "yqwgsr25au"
PASSWORD = "guebgf707f"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive"
}

def fetch_xtream(action: str, category_id: str = None):
    url = f"{XTREAM_URL}/player_api.php?username={USERNAME}&password={PASSWORD}&action={action}"
    if category_id:
        url += f"&category_id={category_id}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Xtream Error Status Code: {response.status_code}")
    except Exception as e:
        print(f"Exception fetching from Xtream ({action}): {e}")
    return []

@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working"}

# 1. جلب التصنيفات
@app.get("/api/categories")
def get_categories():
    categories = fetch_xtream("get_live_categories")
    return categories if isinstance(categories, list) else []

# 2. جلب القنوات
@app.get("/api/channels")
def get_channels(category_id: str = None):
    data = fetch_xtream("get_live_streams", category_id)
    
    if not isinstance(data, list):
        return []

    channels = []
    for item in data:
        stream_id = item.get("stream_id")
        if not stream_id:
            continue
            
        channels.append({
            "id": stream_id,
            "title": item.get("name", "قناة بدون عنوان"),
            "poster": item.get("stream_icon", ""),
            "category_id": item.get("category_id"),
            "stream_url": f"{XTREAM_URL}/live/{USERNAME}/{PASSWORD}/{stream_id}.m3u8"
        })
    return channels
