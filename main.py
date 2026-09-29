from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse
import re

app = FastAPI(title="BIBSSA TV API")

# تفعيل CORS لمنع أي حظر من المتصفح
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= بيانات حساب Xtream IPTV =================
XTREAM_SERVER = "http://milo2080.com:80"
XTREAM_USERNAME = "yqwgsr25au"
XTREAM_PASSWORD = "guebgf707f"

API_BASE = f"{XTREAM_SERVER}/player_api.php?username={XTREAM_USERNAME}&password={XTREAM_PASSWORD}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
    "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
}

def xtream_get(action, params=None):
    """استدعاء API الخاص بسيرفر Xtream Codes"""
    url = f"{API_BASE}&action={action}"
    if params:
        url += "&" + urllib.parse.urlencode(params)
    res = requests.get(url, headers=HEADERS, timeout=12)
    res.raise_for_status()
    return res.json()

# المسار الرئيسي لتأكيد عمل السيرفر
@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working smoothly!"}

# ================= 1. القنوات المباشرة / المباريات =================
@app.get("/api/matches")
def get_matches(category_id: int = Query(None)):
    try:
        params = {"category_id": category_id} if category_id is not None else None
        streams = xtream_get("get_live_streams", params)
        
        if not isinstance(streams, list):
            return {"success": True, "data": []}

        matches = []
        for s in streams:
            matches.append({
                "id": s.get("stream_id"),
                "home_team": (s.get("name") or "")[:60],
                "away_team": "",
                "status": "مباشر 🔴",
                "stream_url": f"{XTREAM_SERVER}/live/{XTREAM_USERNAME}/{XTREAM_PASSWORD}/{s.get('stream_id')}.ts",
                "logo": s.get("stream_icon"),
                "category_id": s.get("category_id"),
                "epg": s.get("epg_channel_id")
            })
        return {"success": True, "data": matches}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ================= 2. الأفلام (VOD) =================
@app.get("/api/movies")
def get_movies(category_id: int = Query(None)):
    try:
        params = {"category_id": category_id} if category_id is not None else None
        movies = xtream_get("get_vod_streams", params)
        
        if not isinstance(movies, list):
            return {"success": True, "data": []}

        data = []
        for m in movies:
            ext = m.get("container_extension", "mp4")
            data.append({
                "id": m.get("stream_id"),
                "title": (m.get("name") or "")[:60],
                "poster": m.get("stream_icon"),
                "stream_url": f"{XTREAM_SERVER}/movie/{XTREAM_USERNAME}/{XTREAM_PASSWORD}/{m.get('stream_id')}.{ext}",
                "category_id": m.get("category_id"),
                "rating": m.get("rating"),
                "year": m.get("year"),
                "duration": m.get("duration")
            })
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ================= 3. المسلسلات =================
@app.get("/api/series")
def get_series(category_id: int = Query(None)):
    try:
        params = {"category_id": category_id} if category_id is not None else None
        series = xtream_get("get_series", params)
        
        if not isinstance(series, list):
            return {"success": True, "data": []}

        data = []
        for s in series:
            data.append({
                "id": s.get("series_id"),
                "title": (s.get("name") or "")[:60],
                "poster": s.get("cover"),
                "backdrop": s.get("backdrop_path"),
                "category_id": s.get("category_id"),
                "rating": s.get("rating"),
                "year": s.get("year")
            })
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ================= 4. حلقات مسلسل =================
@app.get("/api/series/{series_id}/episodes")
def get_series_episodes(series_id: int):
    try:
        info = xtream_get("get_series_info", {"series_id": series_id})
        episodes_data = info.get("episodes", {})
        episodes = []

        if isinstance(episodes_data, dict):
            for season_num, ep_list in episodes_data.items():
                for ep in ep_list:
                    ext = ep.get("container_extension", "mp4")
                    episodes.append({
                        "season": ep.get("season"),
                        "episode": ep.get("episode"),
                        "title": ep.get("title"),
                        "stream_url": f"{XTREAM_SERVER}/series/{XTREAM_USERNAME}/{XTREAM_PASSWORD}/{ep.get('id')}.{ext}"
                    })

        return {"success": True, "data": episodes}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ================= 5. الفئات =================
@app.get("/api/categories/{kind}")
def get_categories(kind: str):
    action_map = {
        "live": "get_live_categories",
        "movies": "get_vod_categories",
        "series": "get_series_categories"
    }
    if kind not in action_map:
        raise HTTPException(404, "Unknown category kind")
    try:
        cats = xtream_get(action_map[kind])
        return {"success": True, "data": cats}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ================= 6. البروكسي لتمرير الفيديو =================
@app.get("/proxy")
def proxy_stream(url: str = Query(...)):
    def stream_content():
        try:
            req_headers = HEADERS.copy()
            req_headers["Referer"] = XTREAM_SERVER
            with requests.get(url, headers=req_headers, stream=True, timeout=15) as req:
                for chunk in req.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
        except Exception:
            pass

    media_type = "application/x-mpegURL" if ".m3u8" in url else "video/mp2t"
    return StreamingResponse(stream_content(), media_type=media_type)
