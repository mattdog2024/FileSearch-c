@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

echo ============================================
echo   FileSearch Build Tool
echo   Auto-install dependencies and package EXE
echo ============================================
echo.

:: Set UTF-8 environment
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install
    pause
    exit /b 1
)

echo [1/4] Checking Python...
python --version
echo.

:: Upgrade pip
echo [2/4] Upgrading pip and installing dependencies...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] pip upgrade failed, continuing...
)

:: Install project dependencies
echo.
echo Installing dependencies (Tsinghua mirror)...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [ERROR] Dependency install failed. Check network connection.
    pause
    exit /b 1
)

:: Install PyInstaller
echo.
echo Installing PyInstaller...
pip install pyinstaller -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller install failed
    pause
    exit /b 1
)

echo.
echo [3/4] Building EXE (using spec file)...
echo.

:: Use spec file for reliable jieba data file bundling
pyinstaller --noconfirm --clean filesearch.spec

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed. Trying command-line method...
    echo.

    :: Fallback: command-line method
    for /f "delims=" %%i in ('python -c "import jieba, os; print(os.path.dirname(jieba.__file__))"') do set JIEBA_PATH=%%i

    pyinstaller --noconfirm --clean ^
        --name "FileSearch" ^
        --windowed ^
        --onefile ^
        --add-data "core;core" ^
        --add-data "ui;ui" ^
        --add-data "%JIEBA_PATH%;jieba" ^
        --hidden-import jieba ^
        --hidden-import jieba.finalseg ^
        --hidden-import jieba._compat ^
        --hidden-import pdfplumber ^
        --hidden-import pdfminer ^
        --hidden-import openpyxl ^
        --hidden-import docx ^
        --hidden-import pptx ^
        --hidden-import olefile ^
        --hidden-import chardet ^
        --hidden-import PyPDF2 ^
        --collect-all jieba ^
        main.py

    if %errorlevel% neq 0 (
        echo [ERROR] Build failed
        pause
        exit /b 1
    )
)

echo.
echo [4/4] Build complete!
echo.
echo ============================================
echo   EXE location: dist\FileSearch.exe
echo   File size:
for %%A in (dist\FileSearch.exe) do echo   %%~zA bytes
echo ============================================
echo.
echo Usage:
echo   1. Copy dist\FileSearch.exe to any folder
echo   2. Double-click to run
echo   3. Index files saved in EXE folder\indexes
echo   4. First launch takes a few seconds for dictionary loading
echo.
echo Encoding notes:
echo   - Built-in UTF-8 support
echo   - Auto-detects GBK/GB18030/UTF-8 files
echo   - Avoid special characters in file paths if issues occur
echo.

:: Ask to open directory
set /p OPEN_DIR="Open EXE folder? (Y/N): "
if /i "%OPEN_DIR%"=="Y" (
    start explorer dist
)

pause
