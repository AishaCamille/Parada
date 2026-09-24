@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    py -3 server.py --open
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3 nao encontrado. Instale o Python e tente novamente.
        pause
        exit /b 1
    )
    python server.py --open
)

if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar o Parada. Veja a mensagem acima.
    pause
    exit /b 1
)
endlocal
