import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BIBSSA TV API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# بيانات سيرفر Xtream التي تعمل برابط HTTP
XTREAM_URL = "http://milo2080.com:80"
USERNAME = "yqwgsr25au"
PASSWORD = "guebgf707f"

# جلسة اتصالات متقدمة لتجاوز حظر HTTP وشهادات الأمان
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

def fetch_xtream(action: str, category_id: str = None):
    url = f"{XTREAM_URL}/player_api.php?username={USERNAME}&password={PASSWORD}&action={action}"
    if category_id:
        url += f"&category_id={category_id}"
    try:
        # verify=False لتجاهل مشاكل الأمان في روابط http والانتظار 15 ثانية
        response = session.get(url, timeout=15, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching from Xtream ({action}): {e}")
    return []

@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working"}

@app.get("/api/categories")
def get_categories():
    categories = fetch_xtream("get_live_categories")
    return categories if isinstance(categories, list) else []

@app.get("/api/channels")
def get_channels(category_id: str = None):
    data = fetch_xtream("get_live_streams", category_id)
    
    if not isinstance(data, list):
        return []

    channels = []
    for item in data:
        stream_id = item.get("stream_id")
        channels.append({
            "id": stream_id,
            "title": item.get("name"),
            "poster": item.get("stream_icon", ""),
            "category_id": item.get("category_id"),
            # جلب البث عبر السيرفر الوسيط أو رابط مباشر
            "stream_url": f"{http://milo2080.com:80}/live/{yqwgsr25au}/{guebgf707f}/{type}.m3u8"
        })
    return channels
