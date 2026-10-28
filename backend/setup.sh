#!/bin/bash
# =====================================================
# اسکریپت راه‌اندازی پروژه بیمارستان
# برای لینوکس (Ubuntu/Debian/CentOS)
# =====================================================

set -e  # خروج در صورت خطا

echo "🚀 شروع راه‌اندازی پروژه..."

# =====================================================
# ۱. بررسی نصب پایتون
# =====================================================
if ! command -v python3 &> /dev/null; then
    echo "❌ پایتون نصب نیست. لطفاً Python 3.12 نصب کنید."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ پایتون نصب است: نسخه $PYTHON_VERSION"

# =====================================================
# ۲. بررسی نصب GTK (برای weasyprint)
# =====================================================
if ! ldconfig -p | grep -q libgobject; then
    echo "⚠️  کتابخانه‌های GTK نصب نیستند. در حال نصب..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
            libffi-dev libjpeg-dev libopenjp2-7-dev libcairo2
    elif command -v yum &> /dev/null; then
        sudo yum install -y pango pango-devel cairo cairo-devel
    fi
fi

# =====================================================
# ۳. ساخت محیط مجازی
# =====================================================
if [ ! -d "myenv" ]; then
    echo "📦 ساخت محیط مجازی..."
    python3 -m venv myenv
fi

# =====================================================
# ۴. فعال‌سازی و نصب پکیج‌ها
# =====================================================
echo "📥 فعال‌سازی محیط مجازی..."
source myenv/bin/activate

echo "⬆️  به‌روزرسانی pip..."
pip install --upgrade pip

echo "📦 نصب پکیج‌ها از requirements.txt..."
pip install -r requirements.txt

# =====================================================
# ۵. ساخت فایل .env اگر وجود ندارد
# =====================================================
if [ ! -f ".env" ]; then
    echo "📝 ساخت فایل .env از نمونه..."
    cp .env.example .env
    echo "⚠️  لطفاً فایل .env را ویرایش کنید و SECRET_KEY را تغییر دهید!"
fi

# =====================================================
# ۶. اجرای migration
# =====================================================
echo "🗄️  اجرای migration..."
python manage.py makemigrations
python manage.py migrate

# =====================================================
# ۷. جمع‌آوری فایل‌های استاتیک (برای production)
# =====================================================
echo "📁 جمع‌آوری فایل‌های استاتیک..."
python manage.py collectstatic --noinput || true

# =====================================================
# ۸. پیام نهایی
# =====================================================
echo ""
echo "=========================================="
echo "✅ راه‌اندازی با موفقیت انجام شد!"
echo "=========================================="
echo ""
echo "برای اجرای سرور:"
echo "  source myenv/bin/activate"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
echo "برای ساخت ادمین:"
echo "  python manage.py createsuperuser"
echo ""