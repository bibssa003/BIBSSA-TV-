import requests
import urllib3
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# تعطيل التحذيرات الخاصة بـ SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="BIBSSA TV API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# بيانات سيرفر Xtream
XTREAM_URL = "http://milo2080.com:80"
USERNAME = "yqwgsr25au"
PASSWORD = "guebgf707f"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
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

# جلب تصنيفات القنوات
@app.get("/api/categories")
def get_categories():
    data = fetch_xtream("get_live_categories")
    return data if isinstance(data, list) else []

# جلب قائمة القنوات المباشرة
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
                # الرابط يمر عبر السيرفر الخاص بك لتجاوز حظر HTTP
                "stream_url": f"https://bibssa-tv.onrender.com/proxy/live/{s_id}.m3u8"
            })
    return result

# جلب تصنيفات الأفلام
@app.get("/api/movie-categories")
def get_movie_categories():
    data = fetch_xtream("get_vod_categories")
    return data if isinstance(data, list) else []

# جلب قائمة الأفلام
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
                "stream_url": f"https://bibssa-tv.onrender.com/proxy/movie/{s_id}.{ext}"
            })
    return result

# بروكسي البث لتجاوز حظر HTTP في متصفحات HTTPS
@app.get("/proxy/live/{stream_id}.m3u8")
def proxy_live(stream_id: str):
    target_url = f"{XTREAM_URL}/live/{USERNAME}/{PASSWORD}/{stream_id}.m3u8"
    try:
        req = requests.get(target_url, headers=HEADERS, stream=True, verify=False, timeout=10)
        return StreamingResponse(req.iter_content(chunk_size=1024), media_type="application/x-mpegURL")
    except Exception as e:
        return Response(content="Error streaming", status_code=500)

@app.get("/proxy/movie/{stream_id}.{ext}")
def proxy_movie(stream_id: str, ext: str):
    target_url = f"{XTREAM_URL}/movie/{USERNAME}/{PASSWORD}/{stream_id}.{ext}"
    try:
        req = requests.get(target_url, headers=HEADERS, stream=True, verify=False, timeout=10)
        return StreamingResponse(req.iter_content(chunk_size=4096), media_type="video/mp4")
    except Exception as e:
        return Response(content="Error streaming", status_code=500)
