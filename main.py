import os
import re
from urllib.parse import urlparse

import requests

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response


# =========================================================
# APP
# =========================================================

app = FastAPI(title="BIBSSA TV M3U API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONFIG
# =========================================================

M3U_URL = os.getenv("M3U_URL", "").strip()


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

# السماح فقط بالدومينات التي تظهر في الـ M3U
allowed_hosts = set()


# =========================================================
# M3U HELPERS
# =========================================================

def parse_attributes(line):
    """
    قراءة attributes الموجودة داخل #EXTINF
    """
    attributes = {}

    matches = re.findall(r'([\w-]+)="([^"]*)"', line)

    for key, value in matches:
        attributes[key] = value

    return attributes


def detect_type(group, title, url):
    """
    محاولة تحديد نوع العنصر:
    live / movie / series
    """

    text = f"{group} {title} {url}".lower()

    movie_words = [
        "movie",
        "movies",
        "film",
        "films",
        "vod",
        "cinema",
        "أفلام",
        "فيلم",
        "سينما",
    ]

    series_words = [
        "series",
        "serie",
        "tv series",
        "مسلسلات",
        "مسلسل",
    ]

    for word in movie_words:
        if word in text:
            return "movie"

    for word in series_words:
        if word in text:
            return "series"

    return "live"


def update_allowed_hosts(items):
    """
    استخراج الدومينات الموجودة فعلياً في M3U.
    هذا يمنع استعمال /proxy كـ Open Proxy لأي موقع.
    """

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


def is_allowed_url(url):
    """
    التأكد أن الرابط تابع لأحد السيرفرات الموجودة في M3U.
    """

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
# M3U PARSER
# =========================================================

def parse_m3u(content):
    items = []

    lines = content.splitlines()

    current_info = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # معلومات القناة
        if line.startswith("#EXTINF"):
            current_info = line
            continue

        # تجاهل باقي تعليمات M3U
        if line.startswith("#"):
            continue

        # رابط القناة
        if current_info:

            attributes = parse_attributes(current_info)

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
                "type": item_type,
            })

            current_info = None

    return items


# =========================================================
# LOAD M3U
# =========================================================

def load_playlist():
    global playlist

    if not M3U_URL:

        print("================================")
        print("ERROR: M3U_URL is empty")
        print("================================")

        playlist = []

        return []


    try:

        print("================================")
        print("Downloading M3U playlist...")
        print("================================")

        response = requests.get(
            M3U_URL,
            headers=HEADERS,
            timeout=60,
            allow_redirects=True,
        )

        print("M3U HTTP status:", response.status_code)

        response.raise_for_status()

        content = response.text

        print("M3U size:", len(content), "characters")

        playlist = parse_m3u(content)

        print("M3U items:", len(playlist))

        update_allowed_hosts(playlist)

        print("================================")

        return playlist

    except Exception as e:

        print(
            "M3U ERROR:",
            type(e).__name__,
            str(e)
        )

        playlist = []

        allowed_hosts.clear()

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
        "items": len(playlist),
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
            [
                x
                for x in playlist
                if x["type"] == "live"
            ]
        ),

        "movies": len(
            [
                x
                for x in playlist
                if x["type"] == "movie"
            ]
        ),

        "series": len(
            [
                x
                for x in playlist
                if x["type"] == "series"
            ]
        ),

        "allowed_hosts": len(allowed_hosts),
    }


# =========================================================
# RELOAD M3U
# =========================================================

@app.get("/api/reload")
def reload_playlist():

    items = load_playlist()

    return {
        "success": True,
        "items_loaded": len(items),
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
            "category_name": group,
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
            set(
                item["group"]
                for item in result
            )
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
            "category_name": group,
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
            set(
                item["group"]
                for item in result
            )
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
            "category_name": group,
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
            set(
                item["group"]
                for item in result
            )
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
# STREAM DIAGNOSTIC
# =========================================================

@app.get("/api/test-stream")
def test_stream(url: str):

    if not url:
        raise HTTPException(
            status_code=400,
            detail="Missing URL"
        )

    # السماح فقط بروابط موجودة في M3U
    if not is_allowed_url(url):

        raise HTTPException(
            status_code=403,
            detail="Stream host is not allowed"
        )

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            stream=True,
            timeout=15,
            allow_redirects=True,
        )

        content_type = (
            response.headers.get("content-type")
            or ""
        )

        content_length = (
            response.headers.get("content-length")
        )

        return {
            "status": "ok",
            "status_code": response.status_code,
            "content_type": content_type,
            "content_length": content_length,
            "final_url": response.url.split("?")[0],
            "server": response.headers.get("server"),
        }

    except Exception as e:

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error": str(e),
        }


# =========================================================
# STREAM PROXY
# =========================================================

@app.get("/proxy")
def proxy(
    request: Request,
    url: str
):

    if not url:

        raise HTTPException(
            status_code=400,
            detail="Missing URL"
        )


    # حماية الـ proxy
    if not is_allowed_url(url):

        raise HTTPException(
            status_code=403,
            detail="Stream host is not allowed"
        )


    try:

        # -------------------------------------------------
        # Headers
        # -------------------------------------------------

        upstream_headers = dict(HEADERS)

        range_header = request.headers.get("range")

        if range_header:
            upstream_headers["Range"] = range_header


        # -------------------------------------------------
        # Request upstream
        # -------------------------------------------------

        response = requests.get(
            url,
            headers=upstream_headers,
            stream=True,
            timeout=(15, 60),
            allow_redirects=True,
        )


        # -------------------------------------------------
        # Check response
        # -------------------------------------------------

        if response.status_code >= 400:

            error_status = response.status_code

            response.close()

            raise HTTPException(
                status_code=502,
                detail=f"Upstream stream returned HTTP {error_status}"
            )


        # -------------------------------------------------
        # Content Type
        # -------------------------------------------------

        content_type = (
            response.headers.get("content-type")
            or "application/octet-stream"
        )


        # -------------------------------------------------
        # Response headers
        # -------------------------------------------------

        response_headers = {}


        # Content-Length
        if response.headers.get("content-length"):

            response_headers["Content-Length"] = (
                response.headers["content-length"]
            )


        # Content-Range
        if response.headers.get("content-range"):

            response_headers["Content-Range"] = (
                response.headers["content-range"]
            )


        # Accept-Ranges
        if response.headers.get("accept-ranges"):

            response_headers["Accept-Ranges"] = (
                response.headers["accept-ranges"]
            )

        else:

            response_headers["Accept-Ranges"] = "bytes"


        # Cache
        response_headers["Cache-Control"] = "no-cache"


        # -------------------------------------------------
        # Stream generator
        # -------------------------------------------------

        def generate():

            try:

                for chunk in response.iter_content(
                    chunk_size=64 * 1024
                ):

                    if chunk:

                        yield chunk

            finally:

                response.close()


        # -------------------------------------------------
        # HTTP status
        # -------------------------------------------------

        status_code = response.status_code


        return StreamingResponse(
            generate(),
            status_code=status_code,
            media_type=content_type,
            headers=response_headers,
        )


    except HTTPException:

        raise


    except requests.exceptions.Timeout:

        raise HTTPException(
            status_code=504,
            detail="Upstream stream timeout"
        )


    except requests.exceptions.ConnectionError as e:

        raise HTTPException(
            status_code=502,
            detail=f"Upstream connection error: {str(e)}"
        )


    except Exception as e:

        raise HTTPException(
            status_code=502,
            detail=f"Proxy error: {type(e).__name__}: {str(e)}"
        )
