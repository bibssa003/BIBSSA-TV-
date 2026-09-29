import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BIBSSA TV API")

# تفعيل CORS كاملاً للسماح بطلبات GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ضع بيانات سيرفر Xtream الخاص بك هنا
XTREAM_URL = "http://YOUR_SERVER_DOMAIN:PORT"  # مثال: http://iptv-provider.com:8080
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"

def fetch_xtream_data(action: str):
    url = f"{XTREAM_URL}/player_api.php?username={USERNAME}&password={PASSWORD}&action={action}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching {action}: {e}")
    return []

@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working smoothly!"}

# جلب البث المباشر من Xtream
@app.get("/api/matches")
def get_live_streams():
    raw_channels = fetch_xtream_data("get_live_streams")
    channels = []
    for item in raw_channels:
        channels.append({
            "id": item.get("stream_id"),
            "title": item.get("name"),
            "category": item.get("category_id"),
            "stream_url": f"{XTREAM_URL}/live/{USERNAME}/{PASSWORD}/{item.get('stream_id')}.m3u8"
        })
    return channels

# جلب الأفلام من Xtream
@app.get("/api/movies")
def get_movies():
    raw_movies = fetch_xtream_data("get_vod_streams")
    movies = []
    for item in raw_movies:
        ext = item.get("container_extension", "mp4")
        movies.append({
            "id": item.get("stream_id"),
            "title": item.get("name"),
            "poster": item.get("stream_icon", ""),
            "stream_url": f"{XTREAM_URL}/movie/{USERNAME}/{PASSWORD}/{item.get('stream_id')}.{ext}"
        })
    return movies

# جلب المسلسلات من Xtream
@app.get("/api/series")
def get_series():
    raw_series = fetch_xtream_data("get_series")
    series_list = []
    for item in raw_series:
        series_list.append({
            "id": item.get("series_id"),
            "title": item.get("name"),
            "poster": item.get("cover", ""),
            "stream_url": f"{XTREAM_URL}/series/{USERNAME}/{PASSWORD}/{item.get('series_id')}.m3u8"
        })
    return series_list
