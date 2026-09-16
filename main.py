from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# تفعيل CORS لتسمح للمتصفح والتطبيق بالاتصال بجميع الروابط
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# بيانات Ugeen الخاصة بك
UGEEN_HOST = "http://ugeen.live:8080"
UGEEN_USER = "kaicer_VIP0nqw7m"
UGEEN_PASS = "8fwca2"

UGEEN_M3U_URL = f"{UGEEN_HOST}/get.php?username={UGEEN_USER}&password={UGEEN_PASS}&type=m3u_plus&output=ts"
BACKUP_M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"

HEADERS = {
    "User-Agent": "VLC/3.0.18 LibVLC/3.0.18",
    "Accept": "*/*"
}

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/fetch-live")
def fetch_live():
    channels = parse_m3u(UGEEN_M3U_URL)
    if not channels:
        channels = parse_m3u(BACKUP_M3U_URL)
    return {"success": True, "count": len(channels), "data": channels}

@app.get("/proxy")
def proxy_stream(url: str = Query(...)):
    def stream_content():
        with requests.get(url, headers=HEADERS, stream=True, timeout=15) as req:
            for chunk in req.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

    return StreamingResponse(stream_content(), media_type="video/mp2t")

def parse_m3u(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []

        lines = response.text.split("\n")
        channels = []
        current_title = ""
        current_group = "عام"

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                # استخراج الفئة تلقائياً من الملف
                if 'group-title="' in line:
                    current_group = line.split('group-title="')[1].split('"')[0]
                else:
                    current_group = "عام"

                # استخراج اسم القناة
                if "," in line:
                    current_title = line.split(",")[-1]

            elif line.startswith("http"):
                channels.append({
                    "title": current_title if current_title else "قناة بث مباشر",
                    "group": current_group if current_group else "عام",
                    "stream_url": line
                })
                current_title = ""
                current_group = "عام"

        return channels
    except Exception:
        return []