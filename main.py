from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MATCHES_URL = "https://live-match.net/"
MOVIES_URL = "https://egybests.live/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.7,en;q=0.3"
}

@app.get("/")
def get_home():
    return FileResponse("index.html")

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")

# --- استخراج المباريات ---
@app.get("/api/matches")
def get_matches():
    matches = []
    try:
        res = requests.get(MATCHES_URL, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for idx, el in enumerate(soup.find_all(['a', 'div'])):
                text = el.get_text(" ", strip=True)
                href = el.get('href') if el.name == 'a' else (el.find('a')['href'] if el.find('a') else '')
                if ("ضد" in text or "vs" in text.lower()) and len(text) < 80:
                    parts = re.split(r'ضد|vs', text, flags=re.IGNORECASE)
                    if len(parts) >= 2 and href:
                        full_href = href if href.startswith('http') else MATCHES_URL.rstrip('/') + '/' + href.lstrip('/')
                        matches.append({
                            "id": idx + 1,
                            "home_team": parts[0].strip()[:25],
                            "away_team": parts[1].strip()[:25],
                            "status": "مباشر 🔴",
                            "match_page": full_href
                        })
    except Exception as e:
        print(f"Matches error: {e}")

    return {"success": True, "data": matches}

# --- استخراج الأفلام ---
@app.get("/api/movies")
def get_movies():
    movies = []
    try:
        res = requests.get(MOVIES_URL, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for card in soup.find_all(['div', 'a']):
                img = card.find('img')
                link = card if card.name == 'a' else card.find('a')
                if img and link:
                    title = (img.get('alt') or card.get_text()).strip()
                    poster = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    href = link.get('href')
                    if title and poster and href and len(title) > 2:
                        full_href = href if href.startswith('http') else MOVIES_URL.rstrip('/') + '/' + href.lstrip('/')
                        movies.append({
                            "title": title[:30],
                            "poster": poster,
                            "details_url": full_href
                        })
    except Exception as e:
        print(f"Movies error: {e}")

    return {"success": True, "data": movies}

# --- استخراج المشغل الحقيقي بعد تخطي الحماية ---
@app.get("/api/get-player")
def get_player(page_url: str = Query(...)):
    if page_url.endswith('.m3u8') or page_url.endswith('.mp4'):
        return {"type": "direct", "url": page_url}

    try:
        session = requests.Session()
        req_headers = HEADERS.copy()
        req_headers["Referer"] = page_url
        res = session.get(page_url, headers=req_headers, timeout=8)
        
        if res.status_code == 200:
            # 1. البحث عن روابط M3U8 مباشرة في الصفحة
            m3u8_links = re.findall(r'https?://[^\'"\s]+\.m3u8[^\'"\s]*', res.text)
            if m3u8_links:
                return {"type": "direct", "url": m3u8_links[0]}

            # 2. البحث عن إطارات المشغل (Iframe) وتجاوز الطبقة الأولى
            soup = BeautifulSoup(res.text, 'html.parser')
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src') or iframe.get('data-src')
                if src and not any(x in src for x in ['facebook', 'twitter', 'google', 'disqus']):
                    if src.startswith('//'):
                        src = "https:" + src
                    # الدخول للإطار الداخلي جلب Stream المباشر
                    try:
                        sub_res = session.get(src, headers={"Referer": page_url, **HEADERS}, timeout=5)
                        sub_m3u8 = re.findall(r'https?://[^\'"\s]+\.m3u8[^\'"\s]*', sub_res.text)
                        if sub_m3u8:
                            return {"type": "direct", "url": sub_m3u8[0]}
                    except:
                        pass
                    return {"type": "iframe", "url": src}
    except Exception as e:
        print(f"Extraction failed: {e}")

    return {"type": "direct", "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"}

# --- بروكسي لفك حجب السيرفرات عند التشغيل ---
@app.get("/proxy")
def proxy_stream(url: str = Query(...)):
    def stream_content():
        try:
            req_headers = HEADERS.copy()
            req_headers["Referer"] = url
            with requests.get(url, headers=req_headers, stream=True, timeout=15) as req:
                for chunk in req.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        except Exception:
            pass

    media_type = "application/x-mpegURL" if ".m3u8" in url else "video/mp2t"
    return StreamingResponse(stream_content(), media_type=media_type)
