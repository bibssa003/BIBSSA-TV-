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
# CONFIGURATION & MULTI-URL LOADER
# =========================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# تخزين القنوات والمضيفين المسموحين
playlist = []
allowed_hosts = set()


def get_m3u_urls():
    """
    جلب جميع روابط M3U من متغيرات البيئة تلقائياً.
    يدعم M3U_URL وكذلك M3U_URL_1, M3U_URL_2, M3U_URL_3 ... إلخ
    """
    urls = []
    
    # فحص القيمة الأساسية M3U_URL أولاً
    main_url = os.getenv("M3U_URL", "").strip()
    if main_url:
        urls.append(main_url)
    
    # البحث عن أي متغير بيئة إضافي يبدأ بـ M3U_URL_
    for key, val in os.environ.items():
        if key.startswith("M3U_URL_") and val.strip():
            urls.append(val.strip())
            
    # إزالة التكرارات مع الحفاظ على الترتيب
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
            
    return unique_urls


# =========================================================
# M3U PARSER
# =========================================================

def parse_m3u_content(content: str):
    """
    تحليل محتوى ملف M3U واستخراج القنوات منها
    """
    items = []
    current_info = None

    for line in content.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#EXTINF:"):
            current_info = line

        elif line.startswith("http://") or line.startswith("https://"):
            if current_info:
                tvg_id = re.search(r'tvg-id="([^"]*)"', current_info)
                tvg_name = re.search(r'tvg-name="([^"]*)"', current_info)
                tvg_logo = re.search(r'tvg-logo="([^"]*)"', current_info)
                group_title = re.search(r'group-title="([^"]*)"', current_info)

                title_split = current_info.rsplit(",", 1)
                title = title_split[-1].strip() if len(title_split) > 1 else "Unknown Stream"

                category = group_title.group(1).strip() if group_title else "Uncategorized"
                cat_lower = category.lower()

                # تحديد نوع المحتوى تلقائياً
                if any(k in cat_lower for k in ["movie", "movies", "افلام", "أفلام", "vodيبدو أنك تشير إلى كود أردت تعديله بناءً على طلب سابق، لكن محادثتنا بدأت الآن من جديد ولم يصلني نص الكود أو التعديلات المطلوب إجراؤها بعد.

يرجى تزويدي بالآتي:
1. **نص الكود** الذي تريد تعديله (سواء كان بلغة Python, JavaScript, React, FastAPI أو أي لغة أخرى).
2. **المواصفات والتعديلات** المطلوبة (إضافة ميزة جديدة، إصلاح أخطاء، تعديل التصميم، أو ضبط الإعدادات).

بمجرد إرسالها، سأقوم بكتابة الكود الكامِل والمعدّل لك مباشرة.
