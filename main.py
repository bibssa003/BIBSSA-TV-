from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import requests
from bs4 import BeautifulSoup
import re
import os

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
    "Referer": MATCHES_URL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

# --- مسارات ملفات PWA والواجهة ---

@app.get("/")
def get_home():
    return FileResponse("index.html")

@app.get("/manifest.json")
def get_manifest():
    return FileResponse("manifest.json")

@app.get("/sw.js")
def get_sw():
    return FileResponse("sw.js", media_type="application/javascript")

# --- محرك الرياضة والمباريات (Live Sports Hub) ---

@app.get("/api/matches")
def get_matches():
    """ كشط جدول مباريات اليوم من live-match.net """
    matches = []
    try:
        res = requests.get(MATCHES_URL, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # البحث عن عناصر المباريات داخل الموقع
            match_cards = soup.find_all(['div', 'a'], class_=re.compile(r'(match|match-card|match-item)'))
            
            for idx, card in enumerate(match_cards):
                teams = card.find_all(class_=re.compile(r'(team|name|title)'))
                status = card.find(class_=re.compile(r'(time|status|score)'))
                link = card.get('href') if card.name == 'a' else (card.find('a')['href'] if card.find('a') else '')

                if len(teams) >= 2:
                    home_team = teams[0].get_text(strip=True)
                    away_team = teams[1].get_text(strip=True)
                    match_status = status.get_text(strip=True) if status else "قريباً"

                    if link and not link.startswith('http'):
                        link = MATCHES_URL.rstrip('/') + '/' + link.lstrip('/')

                    matches.append({
                        "id": idx + 1,
                        "home_team": home_team,
                        "away_team": away_team,
                        "status": match_status,
                        "match_page": link
                    })
    except Exception as e:
        print(f"Error fetching matches: {e}")

    return {"success": True, "count": len(matches), "data": matches}

@app.get("/api/match-servers")
def get_match_servers(page_url: str = Query(...)):
    """ استخراج سيرفرات المشاهدة المباشرة للمباراة """
    servers = []
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            iframes = soup.find_all('iframe')
            for idx, iframe in enumerate(iframes):
                src = iframe.get('src') or iframe.get('data-src')
                if src:
                    if not src.startswith('http'):
                        src = "https:" + src if src.startswith('//') else page_url
                    servers.append({"name": f"سيرفر {idx+1}", "stream_url": src})
    except Exception:
        pass
    return {"servers": servers}

# --- محرك الترفيه والأفلام (Cinema & VOD Hub) ---

@app.get("/api/movies")
def get_movies(page: int = 1, category: str = "all"):
    """ كشط الأفلام والمسلسلات من egybests.live """
    movies = []
    try:
        url = MOVIES_URL if category == "all" else f"{MOVIES_URL}/{category}/"
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all(['div', 'a'], class_=re.compile(r'(movie|item|poster|card)'))

            for item in items:
                title_elem = item.find(class_=re.compile(r'(title|name)'))
                img_elem = item.find('img')
                link_elem = item if item.name == 'a' else item.find('a')

                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    poster = img_elem.get('src') or img_elem.get('data-src') if img_elem else ''
                    link = link_elem.get('href', '')

                    if link and not link.startswith('http'):
                        link = MOVIES_URL.rstrip('/') + '/' + link.lstrip('/')

                    movies.append({
                        "title": title,
                        "poster": poster,
                        "details_url": link
                    })
    except Exception as e:
        print(f"Error fetching movies: {e}")

    return {"success": True, "count": len(movies), "data": movies}

# --- البروكسي العام لتجاوز قيود الحظر و CORS ---

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
