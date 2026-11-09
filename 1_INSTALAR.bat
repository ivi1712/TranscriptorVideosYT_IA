@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo   INSTALACION DEL TRANSCRIPTOR DE YOUTUBE
echo ==========================================
echo.
echo Creando entorno virtual de Python...
py -3 -m venv ".venv" >nul 2>&1
if not errorlevel 1 goto instalar
python -m venv ".venv" >nul 2>&1
if not errorlevel 1 goto instalar
echo.
echo ERROR: No se ha podido crear el entorno de Python.
echo Comprueba primero en PowerShell: py --version
echo Si no funciona, instala Python 3.13 con:
echo winget install -e --id Python.Python.3.13
echo Despues cierra y abre la terminal y vuelve a ejecutar este archivo.
pause
exit /b 1
:instalar
echo Entorno creado correctamente.
echo.
echo Actualizando pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error_paquetes
echo.
echo Instalando dependencias del transcriptor...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error_paquetes
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Instalacion completada correctamente.
echo Edita el archivo .env para anadir tu clave de Groq, si hace falta.
echo Para procesar audio tambien necesitas FFmpeg.
pause
exit /b 0
:error_paquetes
echo.
echo ERROR: No se han podido instalar las dependencias.
echo Comprueba tu conexion a Internet y vuelve a intentarlo.
pause
exit /b 1
