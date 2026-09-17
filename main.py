from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import re

app = FastAPI()

# تفعيل CORS لتسمح للمتصفح والتطبيق بالاتصال بجميع الروابط
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# بيانات المصدر الجديد: Sir TV
SIRTV_BASE_URL = "https://tvsiir.co/"
BACKUP_M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": SIRTV_BASE_URL,
    "Accept": "*/*"
}

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/fetch-live")
def fetch_live():
    channels = fetch_sirtv_channels()
    if not channels:
        channels = parse_m3u(BACKUP_M3U_URL)
    return {"success": True, "count": len(channels), "data": channels}

@app.get("/proxy")
def proxy_stream(url: str = Query(...)):
    def stream_content():
        try:
            with requests.get(url, headers=HEADERS, stream=True, timeout=15) as req:
                for chunk in req.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        except Exception:
            pass

    # تحديد نوع الميديا بناءً على امتداد الرابط (M3U8 أو TS)
    media_type = "application/x-mpegURL" if ".m3u8" in url else "video/mp2t"
    return StreamingResponse(stream_content(), media_type=media_type)

def fetch_sirtv_channels():
    """ جلب القنوات وتصنيفها مباشرة من موقع Sir TV """
    channels = []
    try:
        response = requests.get(SIRTV_BASE_URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []

        # محاولة البحث عن قائمة M3U المباشرة في الموقع إن وجدت
        m3u_links = re.findall(r'href=["\'](http[s]?://[^\'"]+\.m3u[8]?)["\']', response.text)
        if m3u_links:
            return parse_m3u(m3u_links[0])

        # جلب روابط البث المباشرة من أوساق الأعلام والمعاينات (HLS / M3U8)
        streams = re.findall(r'(http[s]?://[^\'"\s]+\.m3u8[^\'"\s]*)', response.text)
        
        for idx, stream_url in enumerate(streams, 1):
            channels.append({
                "title": f"قناة Sir TV {idx}",
                "group": "Sir TV المباشر",
                "stream_url": stream_url
            })

        return channels
    except Exception:
        return []

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
                if 'group-title="' in line:
                    current_group = line.split('group-title="')[1].split('"')[0]
                else:
                    current_group = "عام"

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
    except Excepti
