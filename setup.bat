@echo off
setlocal enableextensions enabledelayedexpansion

:: =========================================================================
:: Resume AI Assistant Setup Script for Windows
:: 
:: This script automates the setup process for the Resume AI Assistant application.
:: It handles the following tasks:
:: - Checking for required dependencies (Python 3.9+, Node.js 14+, uv)
:: - Setting up a Python virtual environment
:: - Installing Python dependencies via uv
:: - Setting up the Next.js frontend
:: - Creating a sample .env.local configuration file
::
:: Usage: setup.bat
:: =========================================================================

echo [INFO] Starting Resume AI Assistant setup...

:: Check for required tools and their versions
echo [INFO] Checking requirements...

:: Check Python version
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is required but not installed. Please install Python 3.9 or newer.
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)
if !PYTHON_MAJOR! LSS 3 (
    echo [ERROR] Python 3.9+ is required, but you have !PYTHON_VERSION!. Please upgrade Python.
    exit /b 1
)
if !PYTHON_MAJOR! EQU 3 if !PYTHON_MINOR! LSS 9 (
    echo [ERROR] Python 3.9+ is required, but you have !PYTHON_VERSION!. Please upgrade Python.
    exit /b 1
)

:: Check Node.js version
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js is required but not installed. Please install Node.js 14 or newer.
    exit /b 1
)

for /f "tokens=1 delims=v" %%a in ('node --version') do set NODE_VERSION=%%a
for /f "tokens=1 delims=." %%a in ("!NODE_VERSION!") do set NODE_MAJOR=%%a
if !NODE_MAJOR! LSS 14 (
    echo [ERROR] Node.js 14+ is required, but you have v!NODE_VERSION!. Please upgrade Node.js.
    exit /b 1
)

:: Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] uv is not installed. Installing uv...
    powershell -Command "iwr https://astral.sh/uv/install.ps1 -useb | iex"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install uv. Please install it manually.
        echo Visit: https://github.com/astral-sh/uv
        exit /b 1
    )
)

:: Check for curl (needed for fallback SpaCy model download)
where curl >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] curl is not installed. It's recommended for fallback SpaCy model downloads.
    echo [WARNING] You may need to install it manually if you encounter SpaCy model installation issues.
)

echo [INFO] All requirements satisfied!

:: Setup Python virtual environment and install dependencies
echo [INFO] Setting up Python virtual environment...

if exist .venv (
    echo [WARNING] Virtual environment already exists. Skipping creation.
) else (
    python -m venv .venv
    echo [INFO] Virtual environment created.
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

echo [INFO] Installing Python dependencies...
uv sync

echo [INFO] Installing SpaCy language models...
:: Try to install the SpaCy model directly first
python -m spacy info >nul 2>nul
if %ERRORLEVEL% equ 0 (
    :: If SpaCy is already installed, try downloading the model
    python -m spacy download en_core_web_sm >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] Failed to download SpaCy model using 'spacy download'. Attempting alternative methods...
        
        :: Create a directory for downloads if it doesn't exist
        if not exist .downloads mkdir .downloads
        
        :: Try direct download with curl
        set SPACY_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl
        set MODEL_FILE=.downloads\en_core_web_sm-3.7.0-py3-none-any.whl
        
        echo [INFO] Downloading SpaCy model directly with curl...
        curl -L -s --fail "%SPACY_MODEL_URL%" -o "%MODEL_FILE%" >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            echo [INFO] Installing downloaded SpaCy model...
            python -m pip install "%MODEL_FILE%" >nul 2>nul
            if %ERRORLEVEL% neq 0 (
                echo [WARNING] Failed to install SpaCy model from local file.
            )
        ) else (
            echo [WARNING] Failed to download SpaCy model with curl.
            echo [INFO] You may need to install SpaCy models manually after setup completes:
            echo    .venv\Scripts\activate.bat
            echo    python -m spacy download en_core_web_sm
        )
    ) else (
        echo [INFO] SpaCy model installed successfully.
    )
) else (
    echo [WARNING] SpaCy not found in the virtual environment. Models will need to be installed later.
    echo [INFO] After setup, you can install SpaCy models manually with:
    echo    .venv\Scripts\activate.bat
    echo    python -m spacy download en_core_web_sm
)

echo [INFO] Python setup complete!

:: Setup Next.js frontend and install dependencies
echo [INFO] Setting up frontend...

if exist nextjs-frontend (
    cd nextjs-frontend
    echo [INFO] Installing Node.js dependencies...
    call npm install
    cd ..
    echo [INFO] Frontend setup complete!
) else (
    echo [ERROR] Frontend directory 'nextjs-frontend' not found. Skipping frontend setup.
)

:: Create a sample .env.local file with configuration template
echo [INFO] Creating sample .env file...

if exist .env.local (
    echo [WARNING] .env.local file already exists. Skipping creation.
) else (
    (
        echo # Application Configuration
        echo PORT=5001
        echo HOST=0.0.0.0
        echo.
        echo # Anthropic API Configuration
        echo ANTHROPIC_API_KEY=your-anthropic-api-key
        echo.
        echo # Logfire Configuration (Optional)
        echo LOGFIRE_API_KEY=your-logfire-api-key
        echo LOGFIRE_PROJECT=resume-ai-assistant
        echo ENVIRONMENT=development
        echo LOG_LEVEL=INFO
        echo LOGFIRE_ENABLED=false
        echo.
        echo # SpaCy Configuration
        echo # If you have network issues downloading SpaCy models, you can specify 
        echo # local model paths here:
        echo # SPACY_MODEL_PATH=C:\path\to\your\en_core_web_sm-3.7.0-py3-none-any.whl
    ) > .env.local
    echo [INFO] .env.local file created. Please update it with your actual API keys.
)

echo [INFO] Setup complete! Here's how to run the application:
echo   1. Start the backend server:
echo      .venv\Scripts\activate.bat ^&^& uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload
echo   2. Start the frontend (in another terminal):
echo      cd nextjs-frontend ^&^& npm run dev
echo   3. Open your browser to http://localhost:3000
echo.
echo Make sure to update your .env.local file with your actual API keys!

if exist .downloads (
    dir /b .downloads\*.whl >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        echo.
        echo [NOTE] Downloaded SpaCy models are available in the .downloads directory.
        echo If you need to reinstall them, you can use:
        echo   .venv\Scripts\activate.bat ^&^& python -m pip install .downloads\en_core_web_sm-*.whl
    )
)

endlocal

:: Exit with success
exit /b 0