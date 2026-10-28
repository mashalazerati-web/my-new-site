# 🏥 راهنمای راه‌اندازی پروژه بیمارستان

## 📋 پیش‌نیازها

### نسخه پایتون
- **Python 3.12** (توصیه شده)
- Python 3.13 یا 3.14 ممکن است با برخی پکیج‌ها (ortools, weasyprint) مشکل داشته باشند.

### سیستم‌عامل
- **ویندوز ۱۰/۱۱** (برای توسعه)
- **Ubuntu 20.04+** یا **Debian 11+** (برای سرور اصلی)

### Node.js (فقط برای فرانت‌اند)
- Node.js 18 LTS یا بالاتر
- npm 9 یا بالاتر

---

## 🖥️ راه‌اندازی روی ویندوز

### قدم ۱: نصب پایتون

1. برو به https://www.python.org/downloads/release/python-31210/
2. فایل `Windows installer (64-bit)` را دانلود کن.
3. موقع نصب **حتماً** این دو تیک را بزن:
   - ☑ Install launcher for all users
   - ☑ Add python.exe to PATH
4. `Install Now` را بزن.
5. CMD را ببند و دوباره باز کن.
6. تست کن: `python --version` → باید `Python 3.12.x` بزند.

### قدم ۲: نصب GTK (برای weasyprint)

1. برو به https://github.com/tschoonj/GTK-for-Windows-Runtime-Installer/releases
2. آخرین نسخه `gtk3-runtime-...-win64.exe` را دانلود کن.
3. نصب کن. **حتماً** تیک `Set up PATH environment variable` را بزن.
4. کامپیوتر را ری‌استارت کن.

### قدم ۳: راه‌اندازی پروژه

روی فایل `setup.bat` دوبار کلیک کن، یا در CMD بزن:

```cmd
cd D:\hospitalproject\backend
setup.bat