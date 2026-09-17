from fastapi import FastAPI, Query
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://google.com",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
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

# --- محرك الرياضة والمباريات ---

@app.get("/api/matches")
def get_matches():
    matches = []
    try:
        res = requests.get(MATCHES_URL, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            elements = soup.find_all(['a', 'div'], class_=lambda c: c and any(x in c.lower() for x in ['match', 'event', 'game', 'albap']))
            
            for idx, el in enumerate(elements):
                text = el.get_text(" ", strip=True)
                href = el.get('href') if el.name == 'a' else (el.find('a')['href'] if el.find('a') else '')
                
                if "ضد" in text or "vs" in text.lower() or "-" in text:
                    parts = re.split(r'ضد|vs|-', text, flags=re.IGNORECASE)
                    if len(parts) >= 2:
                        if href and not href.startswith('http'):
                            href = MATCHES_URL.rstrip('/') + '/' + href.lstrip('/')
                        matches.append({
                            "id": idx + 1,
                            "home_team": parts[0].strip()[:20],
                            "away_team": parts[1].strip()[:20],
                            "status": "مباشر 🔴",
                            "match_page": href if href else MATCHES_URL
                        })
    except Exception as e:
        print(f"Match Error: {e}")

    # خيار احتياطي لضمان عدم ظهور القائمة فارغة
    if not matches:
        matches = [
            {
                "id": 1,
                "home_team": "قناة رياضية حية 1",
                "away_team": "بث مباشر",
                "status": "مباشر 🔴",
                "match_page": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
            },
            {
                "id": 2,
                "home_team": "قناة رياضية حية 2",
                "away_team": "بث مباشر",
                "status": "مباشر 🔴",
                "match_page": "https://iptv-org.github.io/iptv/index.m3u"
            }
        ]

    return {"success": True, "count": len(matches), "data": matches}

@app.get("/api/match-servers")
def get_match_servers(page_url: str = Query(...)):
    servers = []
    if page_url.endswith('.m3u8') or page_url.endswith('.m3u'):
        return {"servers": [{"name": "سيرفر رئيسي", "stream_url": page_url}]}

    try:
        res = requests.get(page_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            m3u8_links = re.findall(r'https?://[^\'"\s]+\.m3u8[^\'"\s]*', res.text)
            for idx, link in enumerate(m3u8_links):
                servers.append({"name": f"سيرفر M3U8 {idx+1}", "stream_url": link})
                
            if not servers:
                for idx, iframe in enumerate(soup.find_all('iframe')):
                    src = iframe.get('src') or iframe.get('data-src')
                    if src:
                        if src.startswith('//'):
                            src = "https:" + src
                        servers.append({"name": f"سيرفر بث {idx+1}", "stream_url": src})
    except Exception:
        pass

    if not servers:
        servers = [{"name": "سيرفر افتراضي", "stream_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"}]

    return {"servers": servers}

# --- محرك الأفلام والسينما ---

@app.get("/api/movies")
def get_movies():
    movies = []
    try:
        res = requests.get(MOVIES_URL, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            cards = soup.find_all(['div', 'a'], class_=lambda c: c and any(x in c.lower() for x in ['movie', 'film', 'item', 'entry', 'post']))

            for card in cards:
                img = card.find('img')
                title_elem = card.find(['h2', 'h3', 'h4', 'span']) or card
                link_elem = card if card.name == 'a' else card.find('a')

                if img and link_elem:
                    title = title_elem.get_text(strip=True)
                    poster = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    link = link_elem.get('href')

                    if title and len(title) > 2 and poster:
                        if not link.startswith('http'):
                            link = MOVIES_URL.rstrip('/') + '/' + link.lstrip('/')
                        movies.append({
                            "title": title[:30],
                            "poster": poster,
                            "details_url": link
                        })
    except Exception as e:
        print(f"Movie Error: {e}")

    if not movies:
        movies = [
            {
                "title": "فيلم تجريبي HD",
                "poster": "https://via.placeholder.com/300x450/00d2ff/000000?text=BIBSSA+TV",
                "details_url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
            }
        ]

    return {"success": True, "count": len(movies), "data": movies}

# --- البروكسي ---

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
