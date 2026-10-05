import os
import re
from urllib.parse import urlparse

import requests

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


# =========================================================
# BIBSSA TV - M3U BACKEND
# =========================================================

app = FastAPI(
    title="BIBSSA TV M3U API",
    version="2.0"
)


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
# CONFIGURATION
# =========================================================

# ضع روابط M3U في Render Environment Variables
# Name: M3U_URL
# Value: رابط M3U أو عدة روابط مفصولة بفواصل أو أسطر جديدة

M3U_URL_RAW = os.getenv("M3U_URL", "").strip()


# =========================================================
# HTTP HEADERS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Connection": "keep-alive",
}


# =========================================================
# GLOBAL DATA
# =========================================================

playlist = []

# الدومينات المسموح للـ proxy الاتصال بها
allowed_hosts = set()


# =========================================================
# PARSE M3U ATTRIBUTES
# =========================================================

def parse_attributes(line):
    attributes = {}
    matches = re.findall(r'([\w-]+)="([^"]*)"', line)
    for key, value in matches:
        attributes[key] = value
    return attributes


# =========================================================
# DETECT ITEM TYPE
# =========================================================

def detect_type(group, title, url):
    text = f"{group} {title} {url}".lower()

    movie_words = [
        "movie", "movies", "film", "films", "vod", "cinema",
        "أفلام", "افلام", "فيلم", "سينما"
    ]

    series_words = [
        "series", "serie", "tv series", "مسلسلات", "مسلسل"
    ]

    for word in movie_words:
        if word in text:
            return "movie"

    for word in series_words:
        if word in text:
            return "series"

    return "live"


# =========================================================
# UPDATE ALLOWED HOSTS
# =========================================================

def update_allowed_hosts(items):
    global allowed_hosts
    hosts = set()

    for item in items:
        stream_url = item.get("stream_url", "")
        try:
            parsed = urlparse(stream_url)
            if parsed.hostname:
                hosts.add(parsed.hostname.lower())
        except Exception:
            pass

    allowed_hosts = hosts
    print("Allowed upstream hosts:", sorted(allowed_hosts))


# =========================================================
# CHECK URL
# =========================================================

def is_allowed_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if not parsed.hostname:
            return False
        hostname = parsed.hostname.lower()
        return hostname in allowed_hosts
    except Exception:
        return False


# =========================================================
# PARSE M3U CONTENT
# =========================================================

def parse_m3u(content, start_id=1):
    items = []
    lines = content.splitlines()
    current_info = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF"):
            current_info = line
            continue

        if line.startswith("#"):
            continue

        if current_info:
            attributes = parse_attributes(current_info)

            # TITLE
            if "," in current_info:
                title = current_info.split(",", 1)[1].strip()
            else:
                title = "Unknown"

            # GROUP
            group = (
                attributes.get("group-title")
                or attributes.get("group")
                or "Other"
            )

            # LOGO
            logo = (
                attributes.get("tvg-logo")
                or attributes.get("logo")
                or ""
            )

            # TVG ID
            tvg_id = attributes.get("tvg-id", "")

            # TYPE
            item_type = detect_type(group, title, line)

            items.append({
                "id": str(start_id + len(items)),
                "title": title,
                "poster": logo,
                "logo": logo,
                "group": group,
                "tvg_id": tvg_id,
                "stream_url": line,
                "type": item_type,
            })

            current_info = None

    return items


# =========================================================
# LOAD ALL M3U PLAYLISTS
# =========================================================

def load_playlist():
    global playlist

    urls = [
        u.strip()
        for u in re.split(r'[\n,]', M3U_URL_RAW)
        if u.strip()
    ]

    if not urls:
        print("================================")
        print("ERROR: M3U_URL is empty")
        print("================================")
        playlist = []
        allowed_hosts.clear()
        return []

    combined_items = []
    print("================================")
    print(f"Loading {len(urls)} M3U playlist source(s)...")
    print("================================")

    for idx, url in enumerate(urls, 1):
        try:
            print(f"[{idx}/{len(urls)}] Fetching: {url}")
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=60,
                allow_redirects=True
            )
            response.raise_for_status()

            content = response.text
            parsed_items = parse_m3u(content, start_id=len(combined_items) + 1)
            combined_items.extend(parsed_items)
            print(f" -> Loaded {len(parsed_items)} items from source {idx}")
        except Exception as e:
            print(f" -> ERROR loading source {idx}: {type(e).__name__}: {str(e)}")

    playlist = combined_items
    print(f"Total Combined M3U Items: {len(playlist)}")

    update_allowed_hosts(playlist)
    print("================================")

    return playlist


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
def startup():
    print("================================")
    print("BIBSSA TV M3U SERVER STARTED")
    print("================================")
    load_playlist()


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "source": "M3U",
        "items": len(playlist),
    }


@app.get("/api/health")
def health():
    return {
        "status": "online",
        "source": "M3U",
        "m3u_configured": bool(M3U_URL_RAW),
        "items_loaded": len(playlist),
        "live_channels": len([x for x in playlist if x["type"] == "live"]),
        "movies": len([x for x in playlist if x["type"] == "movie"]),
        "series": len([x for x in playlist if x["type"] == "series"]),
        "allowed_hosts": len(allowed_hosts),
    }


@app.get("/api/reload")
def reload_playlist():
    items = load_playlist()
    return {
        "success": True,
        "items_loaded": len(items),
    }


@app.get("/api/categories")
def categories():
    groups = sorted(
        set(item["group"] for item in playlist if item["type"] == "live")
    )
    return [
        {"category_id": str(index + 1), "category_name": group}
        for index, group in enumerate(groups)
    ]


@app.get("/api/channels")
def channels(category_id: str = None):
    result = [item for item in playlist if item["type"] == "live"]

    if category_id:
        groups = sorted(set(item["group"] for item in result))
        try:
            index = int(category_id) - 1
            if 0 <= index < len(groups):
                selected_group = groups[index]
                result = [item for item in result if item["group"] == selected_group]
        except ValueError:
            pass

    return result


@app.get("/api/movie-categories")
def movie_categories():
    groups = sorted(
        set(item["group"] for item in playlist if item["type"] == "movie")
    )
    return [
        {"category_id": str(index + 1), "category_name": group}
        for index, group in enumerate(groups)
    ]


@app.get("/api/movies")
def movies(category_id: str = None):
    result = [item for item in playlist if item["type"] == "movie"]

    if category_id:
        groups = sorted(set(item["group"] for item in result))
        try:
            index = int(category_id) - 1
            if 0 <= index < len(groups):
                selected_group = groups[index]
                result = [item for item in result if item["group"] == selected_group]
        except ValueError:
            pass

    return result


@app.get("/api/series-categories")
def series_categories():
    groups = sorted(
        set(item["group"] for item in playlist if item["type"] == "series")
    )
    return [
        {"category_id": str(index + 1), "category_name": group}
        for index, group in enumerate(groups)
    ]


@app.get("/api/series")
def series(category_id: str = None):
    result = [item for item in playlist if item["type"] == "series"]

    if category_id:
        groups = sorted(set(item["group"] for item in result))
        try:
            index = int(category_id) - 1
            if 0 <= index < len(groups):
                selected_group = groups[index]
                result = [item for item in result if item["group"] == selected_group]
        except ValueError:
            pass

    return result


@app.get("/api/test-stream")
def test_stream(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    if not is_allowed_url(url):
        raise HTTPException(status_code=403, detail="Stream host is not allowed")

    response = None
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            stream=True,
            timeout=15,
            allow_redirects=True,
        )
        content_type = response.headers.get("content-type") or ""
        content_length = response.headers.get("content-length")
        final_url = response.url.split("?")[0]

        return {
            "status": "ok",
            "status_code": response.status_code,
            "content_type": content_type,
            "content_length": content_length,
            "final_url": final_url,
            "server": response.headers.get("server"),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error": str(e),
        }
    finally:
        if response:
            response.close()


@app.get("/api/stream-info")
def stream_info(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    if not is_allowed_url(url):
        raise HTTPException(status_code=403, detail="Stream host is not allowed")

    response = None
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            stream=True,
            timeout=15,
            allow_redirects=True,
        )
        content_type = (response.headers.get("content-type") or "").lower()

        if "video/mp2t" in content_type or "mpeg" in content_type:
            stream_type = "mpegts"
        elif "mpegurl" in content_type or "m3u8" in content_type:
            stream_type = "hls"
        elif "video/mp4" in content_type or "mp4" in content_type:
            stream_type = "mp4"
        else:
            stream_type = "unknown"

        return {
            "status": "ok",
            "stream_type": stream_type,
            "content_type": content_type,
            "status_code": response.status_code,
            "final_url": response.url.split("?")[0],
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error": str(e),
        }
    finally:
        if response:
            response.close()


@app.get("/proxy")
def proxy(request: Request, url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    if not is_allowed_url(url):
        raise HTTPException(status_code=403, detail="Stream host is not allowed")

    response = None
    try:
        upstream_headers = dict(HEADERS)
        range_header = request.headers.get("range")
        if range_header:
            upstream_headers["Range"] = range_header

        response = requests.get(
            url,
            headers=upstream_headers,
            stream=True,
            timeout=(15, 60),
            allow_redirects=True,
        )

        if response.status_code >= 400:
            status = response.status_code
            response.close()
            response = None
            raise HTTPException(
                status_code=502,
                detail=f"Upstream stream returned HTTP {status}"
            )

        content_type = response.headers.get("content-type") or "application/octet-stream"
        response_headers = {}

        if response.headers.get("content-length"):
            response_headers["Content-Length"] = response.headers["content-length"]

        if response.headers.get("content-range"):
            response_headers["Content-Range"] = response.headers["content-range"]

        response_headers["Accept-Ranges"] = response.headers.get("accept-ranges", "bytes")
        response_headers["Cache-Control"] = "no-cache"
        response_headers["Access-Control-Allow-Origin"] = "*"

        def generate():
            try:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        yield chunk
            finally:
                response.close()

        return StreamingResponse(
            generate(),
            status_code=response.status_code,
            media_type=content_type,
            headers=response_headers,
        )

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        if response:
            response.close()
        raise HTTPException(status_code=504, detail="Upstream stream timeout")
    except requests.exceptions.ConnectionError as e:
        if response:
            response.close()
        raise HTTPException(
            status_code=502,
            detail=f"Upstream connection error: {str(e)}"
        )
    except Exception as e:
        if response:
            response.close()
        raise HTTPException(
            status_code=502,
            detail=f"Proxy error: {type(e).__name__}: {str(e)}"
        )
