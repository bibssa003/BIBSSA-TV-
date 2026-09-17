from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SIRTV_BASE_URL = "https://tvsiir.co/"
# قائمة احتياطية مجانية مفتوحة المصدر من iptv-org (وليس Ugeen)
BACKUP_M3U_URL = "https://iptv-org.github.io/iptv/index.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": SIRTV_BASE_URL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/fetch-live")
def fetch_live():
    channels = fetch_sirtv_channels()
    # إذا لم يستخرج قنوات من Sir TV، استخدم قائمة IPTV-ORG وليس Ugeen
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

    media_type = "application/x-mpegURL" if ".m3u8" in url else "video/mp2t"
    return StreamingResponse(stream_content(), media_type=media_type)

def fetch_sirtv_channels():
    """ جلب قائمة القنوات وصفحات البث المباشر من Sir TV """
    channels = []
    try:
        response = requests.get(SIRTV_BASE_URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن روابط صفحات القنوات من القائمة والبطاقات
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            title = link.get_text(strip=True)
            
            # فلترة الروابط لاستخراج القنوات المباشرة
            if any(key in href for key in ['/live/', '/channel/', '/tv/']) or (title and len(title) > 2):
                if not href.startswith('http'):
                    href = SIRTV_BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                
                # استخراج رابط البث المباشر المدمج داخل صفحة القناة
                stream_url = extract_stream_from_page(href)
                if stream_url:
                    channels.append({
                        "title": title if title else f"قناة {len(channels)+1}",
                        "group": "Sir TV المباشر",
                        "stream_url": stream_url
                    })

        return channels
    except Exception as e:
        print(f"Error fetching Sir TV: {e}")
        return []

def extract_stream_from_page(page_url):
    """ استخراج رابط الفيديو (m3u8 / iframe) من صفحة القناة """
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=5)
        if res.status_code != 200:
            return None
        
        # 1. البحث عن رابط m3u8 مباشر
        m3u8_matches = re.findall(r'https?://[^\'"\s]+\.m3u8[^\'"\s]*', res.text)
        if m3u8_matches:
            return m3u8_matches[0]
            
        # 2. البحث عن مشغل iframe
        soup = BeautifulSoup(res.text, 'html.parser')
        iframe = soup.find('iframe')
        if iframe and 'src' in iframe.attrs:
            iframe_src = iframe['src']
            if iframe_src.startswith('http'):
                return iframe_src

        return page_url
    except Exception:
        return None

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
    except Exception:
        return []
