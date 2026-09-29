import os
import re
import requests

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(title="BIBSSA TV M3U API")

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# M3U URL
# =========================================================

M3U_URL = os.getenv("M3U_URL", "").strip()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )
}

# =========================================================
# CACHE
# =========================================================

playlist = []


# =========================================================
# M3U ATTRIBUTE PARSER
# =========================================================

def parse_attributes(line):
    attributes = {}

    matches = re.findall(r'([\w-]+)="([^"]*)"', line)

    for key, value in matches:
        attributes[key] = value

    return attributes


# =========================================================
# DETECT TYPE
# =========================================================

def detect_type(group, title, url):

    text = f"{group} {title} {url}".lower()

    # Movies
    movie_words = [
        "movie",
        "movies",
        "film",
        "films",
        "vod",
        "cinema",
        "أفلام",
        "فيلم",
        "سينما"
    ]

    # Series
    series_words = [
        "series",
        "serie",
        "tv series",
        "مسلسلات",
        "مسلسل"
    ]

    for word in movie_words:
        if word in text:
            return "movie"

    for word in series_words:
        if word in text:
            return "series"

    return "live"


# =========================================================
# PARSE M3U
# =========================================================

def parse_m3u(content):

    items = []

    lines = content.splitlines()

    current_info = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # EXTINF
        if line.startswith("#EXTINF"):
            current_info = line
            continue

        # Ignore other M3U tags
        if line.startswith("#"):
            continue

        # Stream URL
        if current_info:

            attributes = parse_attributes(current_info)

            # Name after comma
            if "," in current_info:
                title = current_info.split(",", 1)[1].strip()
            else:
                title = "Unknown"

            group = (
                attributes.get("group-title")
                or attributes.get("group")
                or "Other"
            )

            logo = (
                attributes.get("tvg-logo")
                or attributes.get("logo")
                or ""
            )

            tvg_id = attributes.get("tvg-id", "")

            item_type = detect_type(
                group,
                title,
                line
            )

            items.append({
                "id": str(len(items) + 1),
                "title": title,
                "poster": logo,
                "logo": logo,
                "group": group,
                "tvg_id": tvg_id,
                "stream_url": line,
                "type": item_type
            })

            current_info = None

    return items


# =========================================================
# DOWNLOAD M3U
# =========================================================

def load_playlist():

    global playlist

    if not M3U_URL:

        print("ERROR: M3U_URL is empty")

        playlist = []

        return []

    try:

        print("Downloading M3U playlist...")

        response = requests.get(
            M3U_URL,
            headers=HEADERS,
            timeout=60
        )

        print(
            "M3U HTTP status:",
            response.status_code
        )

        response.raise_for_status()

        content = response.text

        print(
            "M3U size:",
            len(content),
            "characters"
        )

        playlist = parse_m3u(content)

        print(
            "M3U items:",
            len(playlist)
        )

        return playlist

    except Exception as e:

        print(
            "M3U ERROR:",
            type(e).__name__,
            str(e)
        )

        playlist = []

        return []


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
def startup():

    print("================================")
    print("BIBSSA TV M3U SERVER")
    print("================================")

    load_playlist()


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "source": "M3U",
        "items": len(playlist)
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():

    return {
        "status": "online",
        "source": "M3U",
        "m3u_configured": bool(M3U_URL),
        "items_loaded": len(playlist),
        "live_channels": len(
            [x for x in playlist if x["type"] == "live"]
        ),
        "movies": len(
            [x for x in playlist if x["type"] == "movie"]
        ),
        "series": len(
            [x for x in playlist if x["type"] == "series"]
        )
    }


# =========================================================
# RELOAD PLAYLIST
# =========================================================

@app.get("/api/reload")
def reload_playlist():

    items = load_playlist()

    return {
        "success": True,
        "items_loaded": len(items)
    }


# =========================================================
# LIVE CATEGORIES
# =========================================================

@app.get("/api/categories")
def categories():

    groups = sorted(
        set(
            item["group"]
            for item in playlist
            if item["type"] == "live"
        )
    )

    return [
        {
            "category_id": str(index + 1),
            "category_name": group
        }
        for index, group in enumerate(groups)
    ]


# =========================================================
# LIVE CHANNELS
# =========================================================

@app.get("/api/channels")
def channels(category_id: str = None):

    result = [
        item
        for item in playlist
        if item["type"] == "live"
    ]

    if category_id:

        groups = sorted(
            set(item["group"] for item in result)
        )

        try:

            index = int(category_id) - 1

            if 0 <= index < len(groups):

                selected_group = groups[index]

                result = [
                    item
                    for item in result
                    if item["group"] == selected_group
                ]

        except ValueError:
            pass

    return result


# =========================================================
# MOVIE CATEGORIES
# =========================================================

@app.get("/api/movie-categories")
def movie_categories():

    groups = sorted(
        set(
            item["group"]
            for item in playlist
            if item["type"] == "movie"
        )
    )

    return [
        {
            "category_id": str(index + 1),
            "category_name": group
        }
        for index, group in enumerate(groups)
    ]


# =========================================================
# MOVIES
# =========================================================

@app.get("/api/movies")
def movies(category_id: str = None):

    result = [
        item
        for item in playlist
        if item["type"] == "movie"
    ]

    if category_id:

        groups = sorted(
            set(item["group"] for item in result)
        )

        try:

            index = int(category_id) - 1

            if 0 <= index < len(groups):

                selected_group = groups[index]

                result = [
                    item
                    for item in result
                    if item["group"] == selected_group
                ]

        except ValueError:
            pass

    return result


# =========================================================
# SERIES CATEGORIES
# =========================================================

@app.get("/api/series-categories")
def series_categories():

    groups = sorted(
        set(
            item["group"]
            for item in playlist
            if item["type"] == "series"
        )
    )

    return [
        {
            "category_id": str(index + 1),
            "category_name": group
        }
        for index, group in enumerate(groups)
    ]


# =========================================================
# SERIES
# =========================================================

@app.get("/api/series")
def series(category_id: str = None):

    result = [
        item
        for item in playlist
        if item["type"] == "series"
    ]

    if category_id:

        groups = sorted(
            set(item["group"] for item in result)
        )

        try:

            index = int(category_id) - 1

            if 0 <= index < len(groups):

                selected_group = groups[index]

                result = [
                    item
                    for item in result
                    if item["group"] == selected_group
                ]

        except ValueError:
            pass

    return result


# =========================================================
# STREAM PROXY
# =========================================================

@app.get("/proxy")
def proxy(url: str):

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Missing URL"
        )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            stream=True,
            timeout=30
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            "application/octet-stream"
        )

        return StreamingResponse(
            response.iter_content(
                chunk_size=64 * 1024
            ),
            media_type=content_type
        )

    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=str(e)
        )
