from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BIBSSA TV API")

# تفعيل CORS لجميع المصادر لتجنب أخطاء الحظر في المتصفح
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "online", "message": "BIBSSA TV API is working smoothly!"}

# مسار جلب القنوات والمباريات المباشرة
@app.get("/api/matches")
def get_matches():
    return [
        {
            "id": 1,
            "title": "beIN Sports 1",
            "category": "رياضة",
            "stream_url": "https://example.com/stream1.m3u8"
        },
        {
            "id": 2,
            "title": "MBC 1",
            "category": "ترفيه",
            "stream_url": "https://example.com/stream2.m3u8"
        }
    ]

# مسار جلب الأفلام
@app.get("/api/movies")
def get_movies():
    return [
        {
            "id": 101,
            "title": "اسم الفيلم التجريبي",
            "poster": "https://via.placeholder.com/150",
            "stream_url": "https://example.com/movie1.mp4"
        }
    ]

# مسار جلب المسلسلات
@app.get("/api/series")
def get_series():
    return [
        {
            "id": 201,
            "title": "اسم المسلسل التجريبي",
            "poster": "https://via.placeholder.com/150",
            "episodes": []
        }
    ]
