import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BIBSSA TV API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ استبدل هذه البيانات ببيانات سيرفر Xtream الخاص بك
XTREAM_URL = "http://milo2080.com:80"
USERNAME = "yqwgsr25au"
PASSWORD = "guebgf707f"

def fetch_xtream(action: str, category_id: str = None):
    url = f"{XTREAM_URL}/player_api.php?username={USERNAME}&password={PASSWORD}&action={action}"
    if category_id:
        url += f"&category_id={category_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching from Xtream ({action}): {e}")
    return []

@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working smoothly!"}

# 1. جلب التصنيفات (Categories) حسب النوع (live / movies / series)
@app.get("/api/categories/{content_type}")
def get_categories(content_type: str):
    action_map = {
        "live": "get_live_categories",
        "movies": "get_vod_categories",
        "series": "get_series_categories"
    }
    action = action_map.get(content_type, "get_live_categories")
    categories = fetch_xtream(action)
    return categories if isinstance(categories, list) else []

# 2. جلب المحتوى (قنوات / أفلام / مسلسلات) مع إمكانية التصفية بحسب التصنيف category_id
@app.get("/api/content/{content_type}")
def get_content(content_type: str, category_id: str = None):
    action_map = {
        "live": "get_live_streams",
        "movies": "get_vod_streams",
        "series": "get_series"
    }
    action = action_map.get(content_type, "get_live_streams")
    data = fetch_xtream(action, category_id)
    
    if not isinstance(data, list):
        return []

    items = []
    for item in data:
        if content_type == "live":
            stream_id = item.get("stream_id")
            items.append({
                "id": stream_id,
                "title": item.get("name"),
                "poster": item.get("stream_icon", ""),
                "category_id": item.get("category_id"),
                "stream_url": f"{XTREAM_URL}/live/{USERNAME}/{PASSWORD}/{stream_id}.m3u8"
            })
        elif content_type == "movies":
            stream_id = item.get("stream_id")
            ext = item.get("container_extension", "mp4")
            items.append({
                "id": stream_id,
                "title": item.get("name"),
                "poster": item.get("stream_icon", ""),
                "category_id": item.get("category_id"),
                "stream_url": f"{XTREAM_URL}/movie/{USERNAME}/{PASSWORD}/{stream_id}.{ext}"
            })
        elif content_type == "series":
            series_id = item.get("series_id")
            items.append({
                "id": series_id,
                "title": item.get("name"),
                "poster": item.get("cover", ""),
                "category_id": item.get("category_id"),
                "stream_url": f"{XTREAM_URL}/series/{USERNAME}/{PASSWORD}/{series_id}.m3u8"
            })
    return items
