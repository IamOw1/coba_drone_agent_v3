@echo off
REM 🚁 COBA AI Drone Agent 2.0 - Скрипт быстрого запуска для Windows
REM Используйте: run.bat [mode] [options]

setlocal enabledelayedexpansion

set "MODE=%1"
if "%MODE%"=="" set "MODE=help"
shift

:check_python
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python не найден!
    echo Установите Python 3.8+ и попробуйте снова
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION%

:main
if "%MODE%"=="check" (
    echo Проверка целостности системы...
    python check_system.py
    exit /b
)
if "%MODE%"=="demo" (
    echo Запуск интерактивной демонстрации...
    python demo.py
    exit /b
)
if "%MODE%"=="agent" (
    echo 🚁 Запуск агента...
    python main.py agent
    exit /b
)
if "%MODE%"=="api" (
    echo 🚁 Запуск API сервера...
    python main.py api %*
    exit /b
)
if "%MODE%"=="dashboard" (
    echo 🚁 Запуск дашборда...
    python main.py dashboard
    exit /b
)
if "%MODE%"=="all" (
    echo 🚁 Запуск всех компонентов...
    python main.py all
    exit /b
)

:show_help
echo.
echo ════════════════════════════════════════════════════════════════
echo 🚁 COBA AI Drone Agent 2.0 - Быстрый запуск
echo ════════════════════════════════════════════════════════════════
echo.
echo Использование:
echo   run.bat [mode] [options]
echo.
echo Режимы (mode):
echo   check      Проверка целостности системы
echo   demo       Интерактивная демонстрация
echo   agent      Запуск только агента
echo   api        Запуск API сервера (по умолчанию на порту 8000)
echo   dashboard  Запуск веб-дашборда (по умолчанию на порту 8501)
echo   all        Запуск всего (агент + API + дашборд)
echo   help       Показать эту справку
echo.
echo Примеры:
echo   run.bat check              # Проверить систему
echo   run.bat demo               # Запустить демонстрацию
echo   run.bat agent              # Запустить агента
echo   run.bat api --port 9000    # API на порту 9000
echo   run.bat dashboard          # Запустить дашборд
echo   run.bat all                # Все сразу
echo.
