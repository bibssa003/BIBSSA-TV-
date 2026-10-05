import re
import unicodedata

def step1_lowercase_and_normalize(raw_name: str) -> str:
    if not raw_name:
        return ""

    # 1. تحويل الحروف الإنجليزية إلى صغيرة
    text = raw_name.lower()

    # 2. توحيد الترميز النصي (إزالة الزخارف وتوحيد أشكال الأحرف)
    text = unicodedata.normalize('NFKC', text)

    # 3. استبدال التابات والأسطر والمسافات المتعددة بمسافة واحدة
    text = re.sub(r'\s+', ' ', text)

    # 4. إزالة المسافات الزائدة من البداية والنهاية
    return text.strip()
