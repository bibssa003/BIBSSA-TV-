import os
import base64
from urllib.parse import urlparse, urljoin

import requests
import urllib3

from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="BIBSSA TV API")

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# XTREAM CONFIG
# =========================================================

XTREAM_URL = os.getenv("XTREAM_URL", "http://milo2080.com:80").rstrip("/")
USERNAME = os.getenv("XTREAM_USERNAME", "yqwgsr25au")
PASSWORD = os.getenv("XTREAM_PASSWORD", "guebgf707f")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# =========================================================
# HELPERS
# =========================================================

def xtream_api(action=None, extra_params=None):
    """
    الاتصال بـ Xtream player_api.php
    """

    params = {
        "username": USERNAME,
        "password": PASSWORD,
    }

    if action:
        params["action"] = action

    if extra_params:
        params.update(extra_params)

    try:
        response = requests.get(
            f"{XTREAM_URL}/player_api.php",
            params=params,
            headers=HEADERS,
            timeout=20,
            verify=False,
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print(f"Xtream API Error: {e}")
        return []


def encode_url(url):
    """
    تحويل الرابط إلى token آمن للاستخدام في URL.
    """
    return base64.urlsafe_b64encode(
        url.encode("utf-8")
    ).decode("utf-8").rstrip("=")


def decode_url(token):
    """
    استرجاع الرابط من token.
    """
    padding = "=" * (-len(token) % 4)

    return base64.urlsafe_b64decode(
        token + padding
    ).decode("utf-8")


def is_allowed_upstream(url):
    """
    منع استخدام البروكسي للوصول إلى مواقع خارج سيرفر Xtream.
    """

    try:
        target = urlparse(url)
        base = urlparse(XTREAM_URL)

        return (
            target.scheme in ("http", "https")
            and target.hostname == base.hostname
        )

    except Exception:
        return False


def safe_image(url):
    if not url:
        return ""

    return str(url)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "BIBSSA TV API"
    }


# =========================================================
# LIVE CATEGORIES
# =========================================================

@app.get("/api/categories")
def get_categories():

    data = xtream_api("get_live_categories")

    if not isinstance(data, list):
        return []

    return [
        {
            "category_id": str(item.get("category_id", "")),
            "category_name": item.get(
                "category_name",
                "بدون تصنيف"
            )
        }
        for item in data
    ]


# =========================================================
# LIVE CHANNELS
# =========================================================

@app.get("/api/channels")
def get_channels(category_id: str = None):

    params = {}

    if category_id:
        params["category_id"] = category_id

    data = xtream_api(
        "get_live_streams",
        params
    )

    if not isinstance(data, list):
        return []

    result = []

    for item in data:

        stream_id = item.get("stream_id")

        if not stream_id:
            continue

        result.append({
            "id": str(stream_id),
            "title": item.get(
                "name",
                "قناة"
            ),
            "poster": safe_image(
                item.get("stream_icon", "")
            ),
            "type": "live",

            "stream_url":
                f"/proxy/live/{stream_id}.m3u8"
        })

    return result


# =========================================================
# MOVIE CATEGORIES
# =========================================================

@app.get("/api/movie-categories")
def get_movie_categories():

    data = xtream_api(
        "get_vod_categories"
    )

    if not isinstance(data, list):
        return []

    return [
        {
            "category_id": str(
                item.get("category_id", "")
            ),
            "category_name": item.get(
                "category_name",
                "بدون تصنيف"
            )
        }
        for item in data
    ]


# =========================================================
# MOVIES
# =========================================================

@app.get("/api/movies")
def get_movies(category_id: str = None):

    params = {}

    if category_id:
        params["category_id"] = category_id

    data = xtream_api(
        "get_vod_streams",
        params
    )

    if not isinstance(data, list):
        return []

    result = []

    for item in data:

        stream_id = item.get("stream_id")

        if not stream_id:
            continue

        extension = item.get(
            "container_extension",
            "mp4"
        )

        result.append({
            "id": str(stream_id),

            "title": item.get(
                "name",
                "فيلم"
            ),

            "poster": safe_image(
                item.get(
                    "stream_icon",
                    ""
                )
            ),

            "type": "movie",

            "stream_url":
                f"/proxy/movie/{stream_id}.{extension}"
        })

    return result


# =========================================================
# SERIES CATEGORIES
# =========================================================

@app.get("/api/series-categories")
def get_series_categories():

    data = xtream_api(
        "get_series_categories"
    )

    if not isinstance(data, list):
        return []

    return [
        {
            "category_id": str(
                item.get("category_id", "")
            ),
            "category_name": item.get(
                "category_name",
                "بدون تصنيف"
            )
        }
        for item in data
    ]


# =========================================================
# SERIES LIST
# =========================================================

@app.get("/api/series")
def get_series(category_id: str = None):

    params = {}

    if category_id:
        params["category_id"] = category_id

    data = xtream_api(
        "get_series",
        params
    )

    if not isinstance(data, list):
        return []

    result = []

    for item in data:

        series_id = item.get("series_id")

        if not series_id:
            continue

        result.append({
            "id": str(series_id),

            "title": item.get(
                "name",
                "مسلسل"
            ),

            "poster": safe_image(
                item.get(
                    "cover",
                    ""
                )
            ),

            "type": "series",

            "plot": item.get(
                "plot",
                ""
            ),

            "rating": item.get(
                "rating",
                ""
            )
        })

    return result


# =========================================================
# SERIES INFO
# =========================================================

@app.get("/api/series/{series_id}")
def get_series_info(series_id: str):

    data = xtream_api(
        "get_series_info",
        {
            "series_id": series_id
        }
    )

    if not isinstance(data, dict):
        return {
            "info": {},
            "seasons": []
        }

    info = data.get("info", {})

    raw_episodes = data.get(
        "episodes",
        {}
    )

    seasons = []

    # Xtream عادة يعيد episodes كـ:
    #
    # {
    #   "1": [...],
    #   "2": [...]
    # }

    if isinstance(raw_episodes, dict):

        for season_number, episodes in raw_episodes.items():

            season_episodes = []

            if not isinstance(
                episodes,
                list
            ):
                continue

            for episode in episodes:

                episode_id = episode.get(
                    "id"
                )

                if not episode_id:
                    continue

                extension = episode.get(
                    "container_extension",
                    "mp4"
                )

                episode_title = episode.get(
                    "title"
                ) or episode.get(
                    "name"
                ) or f"الحلقة {episode.get('episode_num', '')}"

                image = ""

                episode_info = episode.get(
                    "info",
                    {}
                )

                if isinstance(
                    episode_info,
                    dict
                ):
                    image = (
                        episode_info.get(
                            "movie_image"
                        )
                        or episode_info.get(
                            "cover_big"
                        )
                        or ""
                    )

                season_episodes.append({
                    "id": str(
                        episode_id
                    ),

                    "title": episode_title,

                    "episode_num": episode.get(
                        "episode_num",
                        ""
                    ),

                    "season": str(
                        season_number
                    ),

                    "poster": safe_image(
                        image
                    ),

                    "type": "episode",

                    "stream_url":
                        f"/proxy/series/"
                        f"{episode_id}."
                        f"{extension}"
                })

            seasons.append({
                "season": str(
                    season_number
                ),

                "episodes":
                    season_episodes
            })

    # ترتيب المواسم
    seasons.sort(
        key=lambda x: int(x["season"])
        if str(x["season"]).isdigit()
        else 999
    )

    return {
        "info": {
            "name": info.get(
                "name",
                ""
            ),
            "cover": safe_image(
                info.get(
                    "cover",
                    ""
                )
            ),
            "plot": info.get(
                "plot",
                ""
            ),
            "genre": info.get(
                "genre",
                ""
            ),
            "rating": info.get(
                "rating",
                ""
            )
        },

        "seasons": seasons
    }


# =========================================================
# LIVE HLS PROXY
# =========================================================

@app.get("/proxy/live/{stream_id}.m3u8")
def proxy_live(stream_id: str):

    target_url = (
        f"{XTREAM_URL}/live/"
        f"{USERNAME}/"
        f"{PASSWORD}/"
        f"{stream_id}.m3u8"
    )

    try:

        response = requests.get(
            target_url,
            headers=HEADERS,
            timeout=15,
            verify=False
        )

        if response.status_code != 200:
            return Response(
                content="Upstream stream unavailable",
                status_code=response.status_code
            )

        content_type = response.headers.get(
            "content-type",
            "application/vnd.apple.mpegurl"
        )

        playlist = response.text

        # إعادة كتابة روابط HLS
        # حتى يمر كل شيء عبر Render

        lines = playlist.splitlines()

        new_lines = []

        for line in lines:

            stripped = line.strip()

            if not stripped:
                new_lines.append("")
                continue

            # تعليق HLS
            if stripped.startswith("#"):

                # أحيانًا URI داخل EXT-X-KEY
                if 'URI="' in stripped:

                    try:
                        start = stripped.index(
                            'URI="'
                        ) + 5

                        end = stripped.index(
                            '"',
                            start
                        )

                        key_url = stripped[
                            start:end
                        ]

                        absolute_url = urljoin(
                            target_url,
                            key_url
                        )

                        if is_allowed_upstream(
                            absolute_url
                        ):

                            token = encode_url(
                                absolute_url
                            )

                            proxy_url = (
                                f"/proxy/hls/"
                                f"{token}"
                            )

                            stripped = (
                                stripped[:start]
                                + proxy_url
                                + stripped[end:]
                            )

                    except Exception:
                        pass

                new_lines.append(
                    stripped
                )

                continue

            # رابط Segment أو Playlist فرعي
            absolute_url = urljoin(
                target_url,
                stripped
            )

            if is_allowed_upstream(
                absolute_url
            ):

                token = encode_url(
                    absolute_url
                )

                new_lines.append(
                    f"/proxy/hls/{token}"
                )

            else:
                new_lines.append(
                    stripped
                )

        new_playlist = "\n".join(
            new_lines
        )

        return Response(
            content=new_playlist,
            media_type=content_type,
            headers={
                "Cache-Control": "no-cache",
                "Access-Control-Allow-Origin": "*"
            }
        )

    except Exception as e:

        print(
            f"Live proxy error: {e}"
        )

        return Response(
            content="Error streaming live channel",
            status_code=500
        )


# =========================================================
# GENERIC HLS PROXY
# =========================================================

@app.get("/proxy/hls/{token}")
def proxy_hls(token: str):

    try:

        target_url = decode_url(
            token
        )

        if not is_allowed_upstream(
            target_url
        ):
            raise HTTPException(
                status_code=403,
                detail="Invalid upstream URL"
            )

        response = requests.get(
            target_url,
            headers=HEADERS,
            timeout=15,
            verify=False
        )

        if response.status_code != 200:
            return Response(
                content="HLS resource unavailable",
                status_code=response.status_code
            )

        content_type = response.headers.get(
            "content-type",
            ""
        )

        # إذا كان هذا Playlist
        if (
            "mpegurl" in content_type.lower()
            or target_url.lower().endswith(
                ".m3u8"
            )
        ):

            playlist = response.text

            lines = playlist.splitlines()

            new_lines = []

            for line in lines:

                stripped = line.strip()

                if not stripped:
                    new_lines.append("")
                    continue

                if stripped.startswith("#"):

                    if 'URI="' in stripped:

                        try:

                            start = stripped.index(
                                'URI="'
                            ) + 5

                            end = stripped.index(
                                '"',
                                start
                            )

                            child_url = stripped[
                                start:end
                            ]

                            absolute_url = urljoin(
                                target_url,
                                child_url
                            )

                            if is_allowed_upstream(
                                absolute_url
                            ):

                                child_token = encode_url(
                                    absolute_url
                                )

                                stripped = (
                                    stripped[:start]
                                    + "/proxy/hls/"
                                    + child_token
                                    + stripped[end:]
                                )

                        except Exception:
                            pass

                    new_lines.append(
                        stripped
                    )

                    continue

                absolute_url = urljoin(
                    target_url,
                    stripped
                )

                if is_allowed_upstream(
                    absolute_url
                ):

                    child_token = encode_url(
                        absolute_url
                    )

                    new_lines.append(
                        f"/proxy/hls/{child_token}"
                    )

                else:
                    new_lines.append(
                        stripped
                    )

            return Response(
                content="\n".join(
                    new_lines
                ),
                media_type=content_type,
                headers={
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*"
                }
            )

        # TS / binary
        return Response(
            content=response.content,
            media_type=content_type
            or "video/mp2t",
            headers={
                "Access-Control-Allow-Origin": "*"
            }
        )

    except HTTPException:
        raise

    except Exception as e:

        print(
            f"HLS proxy error: {e}"
        )

        return Response(
            content="Error fetching HLS resource",
            status_code=500
        )


# =========================================================
# VIDEO PROXY
# =========================================================

def proxy_video(
    target_url: str,
    request: Request
):

    headers = dict(
        HEADERS
    )

    # دعم التحميل الجزئي للفيديو
    range_header = request.headers.get(
        "range"
    )

    if range_header:
        headers["Range"] = range_header

    try:

        response = requests.get(
            target_url,
            headers=headers,
            stream=True,
            timeout=30,
            verify=False
        )

        response_headers = {}

        for header in [
            "content-length",
            "content-range",
            "accept-ranges",
            "etag",
            "last-modified"
        ]:

            value = response.headers.get(
                header
            )

            if value:
                response_headers[
                    header
                ] = value

        content_type = response.headers.get(
            "content-type",
            "video/mp4"
        )

        return StreamingResponse(
            response.iter_content(
                chunk_size=64 * 1024
            ),
            status_code=response.status_code,
            media_type=content_type,
            headers=response_headers
        )

    except Exception as e:

        print(
            f"Video proxy error: {e}"
        )

        return Response(
            content="Error streaming video",
            status_code=500
        )


# =========================================================
# MOVIE PROXY
# =========================================================

@app.get("/proxy/movie/{stream_id}.{ext}")
def proxy_movie(
    stream_id: str,
    ext: str,
    request: Request
):

    allowed_extensions = {
        "mp4",
        "mkv",
        "avi",
        "mov",
        "webm"
    }

    if ext.lower() not in allowed_extensions:
        ext = "mp4"

    target_url = (
        f"{XTREAM_URL}/movie/"
        f"{USERNAME}/"
        f"{PASSWORD}/"
        f"{stream_id}.{ext}"
    )

    return proxy_video(
        target_url,
        request
    )


# =========================================================
# SERIES EPISODE PROXY
# =========================================================

@app.get("/proxy/series/{episode_id}.{ext}")
def proxy_series(
    episode_id: str,
    ext: str,
    request: Request
):

    allowed_extensions = {
        "mp4",
        "mkv",
        "avi",
        "mov",
        "webm"
    }

    if ext.lower() not in allowed_extensions:
        ext = "mp4"

    target_url = (
        f"{XTREAM_URL}/series/"
        f"{USERNAME}/"
        f"{PASSWORD}/"
        f"{episode_id}.{ext}"
    )

    return proxy_video(
        target_url,
        request
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "xtream_configured": (
            USERNAME != "YOUR_USERNAME"
            and PASSWORD != "YOUR_PASSWORD"
            and "YOUR-XTREAM-SERVER"
            not in XTREAM_URL
        )
    }
