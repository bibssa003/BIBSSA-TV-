import requests
import urllib3
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="BIBSSA TV API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

XTREAM_URL = "http://milo2080.com:80"
USERNAME = "yqwgsr25au"
PASSWORD = "guebgf707f"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_xtream(action: str, category_id: str = None):
    url = f"{XTREAM_URL}/player_api.php?username={USERNAME}&password={PASSWORD}&action={action}"
    if category_id:
        url += f"&category_id={category_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Error fetching {action}: {e}")
    return []

@app.get("/")
def home():
    return {"status": "online"}

# --- القنوات المباشرة ---
@app.get("/api/categories")
def get_categories():
    data = fetch_xtream("get_live_categories")
    return data if isinstance(data, list) else []

@app.get("/api/channels")
def get_channels(category_id: str = None):
    data = fetch_xtream("get_live_streams", category_id)
    if not isinstance(data, list):
        return []
    
    result = []
    for item in data:
        s_id = item.get("stream_id")
        if s_id:
            result.append({
                "id": s_id,
                "title": item.get("name", "قناة"),
                "poster": item.get("stream_icon", ""),
                "type": "live",
                "stream_url": f"{XTREAM_URL}/live/{USERNAME}/{PASSWORD}/{s_id}.m3u8"
            })
    return result

# --- الأفلام (VOD) ---
@app.get("/api/movie-categories")
def get_movie_categories():
    data = fetch_xtream("get_vod_categories")
    return data if isinstance(data, list) else []

@app.get("/api/movies")
def get_movies(category_id: str = None):
    data = fetch_xtream("get_vod_streams", category_id)
    if not isinstance(data, list):
        return []
    
    result = []
    for item in data:
        s_id = item.get("stream_id")
        ext = item.get("container_extension", "mp4")
        if s_id:
            result.append({
                "id": s_id,
                "title": item.get("name", "فيلم"),
                "poster": item.get("stream_icon", ""),
                "type": "movie",
                "stream_url": f"{XTREAM_URL}/movie/{USERNAME}/{PASSWORD}/{s_id}.{ext}"
            })
    return result
