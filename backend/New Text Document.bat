@echo off
echo === Checking Django in virtual environment ===

python -c "import sys, django; sys.exit(0 if 'myenv' in django.__file__.lower() else 1)" >nul 2>&1

if %errorlevel%==0 (
    echo [OK] Django is installed inside myenv.
    echo Path:
    python -c "import django; print(django.__file__)"
) else (
    echo [MISSING] Django is NOT installed in myenv. Installing dependencies...
    python -m pip install Django djangorestframework djangorestframework-simplejwt django-cors-headers jdatetime openpyxl weasyprint Pillow pandas numpy scipy scikit-learn python-decouple
    if %errorlevel%==0 (
        echo [DONE] Installation finished.
        python -c "import django; print(django.__file__)"
    ) else (
        echo [ERROR] Installation failed. Check the output above.
    )
)

pause