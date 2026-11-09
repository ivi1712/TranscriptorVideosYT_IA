"""Transcriptor personal de vídeos de YouTube: subtítulos o Whisper en Groq.

Requisitos: youtube-transcript-api, yt-dlp, groq, python-dotenv.
FFmpeg + ffprobe solo se usan si hace falta transcribir audio.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

BASE_DIR = Path(__file__).resolve().parent
RESULTADOS = BASE_DIR / "transcripciones"
LENGUAJES = ["es", "en"]  # Preferir subtítulos españoles; después ingleses.
MODELO = "whisper-large-v3-turbo"
TAMANO_BLOQUE_SEGUNDOS = 45
MAX_CARACTERES_BLOQUE = 700
DURACION_PARTE_SEGUNDOS = 25 * 60  # MP3 mono 48 kb/s: normalmente <10 MB por parte.


def obtener_id(url: str) -> str:
    """Admite watch, youtu.be, shorts y live; rechaza otros dominios."""
    url = url.strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Introduce una dirección https:// de YouTube.")
    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = parsed.path.strip("/").split("/")
            video_id = parts[1] if len(parts) == 2 and parts[0] in {"shorts", "live", "embed"} else ""
    else:
        raise ValueError("La dirección debe pertenecer a YouTube o youtu.be.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("No he encontrado un identificador de vídeo válido en el enlace.")
    return video_id


def titulo_oembed(url: str, video_id: str) -> str:
    """Intentar obtener el título; si falla, utilizar el identificador."""
    endpoint = "https://www.youtube.com/oembed?url=" + (
        "https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3D" + video_id
    ) + "&format=json"
    try:
        with urlopen(Request(endpoint, headers={"User-Agent": "Mozilla/5.0"}), timeout=7) as response:
            return str(json.load(response).get("title") or video_id)
    except Exception:
        return video_id


def nombre_seguro(texto: str) -> str:
    return (re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", texto).strip(" .")[:75] or "Video")


def marca_tiempo(segundos: float) -> str:
    segundos = max(0, int(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}" if horas else f"{minutos:02d}:{segundos:02d}"


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(texto)).strip()


def agrupar_segmentos(segmentos: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Agrupa frases en párrafos de longitud cómoda, conservando los tiempos."""
    agrupados: list[tuple[float, str]] = []
    inicio: float | None = None
    palabras: list[str] = []
    longitud = 0
    for instante, texto in segmentos:
        texto = limpiar(texto)
        if not texto:
            continue
        if inicio is not None and (
            instante - inicio >= TAMANO_BLOQUE_SEGUNDOS or longitud + len(texto) >= MAX_CARACTERES_BLOQUE
        ):
            agrupados.append((inicio, " ".join(palabras)))
            inicio = None
            palabras = []
            longitud = 0
        if inicio is None:
            inicio = instante
        palabras.append(texto)
        longitud += len(texto) + 1
    if palabras and inicio is not None:
        agrupados.append((inicio, " ".join(palabras)))
    return agrupados


def probar_subtitulos(video_id: str) -> tuple[list[tuple[float, str]], str]:
    transcripcion = YouTubeTranscriptApi().fetch(video_id, languages=LENGUAJES)
    segmentos = [(float(s.start), s.text) for s in transcripcion]
    if not segmentos:
        raise RuntimeError("Subtítulos vacíos")
    tipo = "generados automáticamente" if transcripcion.is_generated else "publicados manualmente"
    return segmentos, f"Subtítulos de YouTube ({transcripcion.language_code}, {tipo})"


def ejecutar(comando: list[str], explicacion: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(comando, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Falta una herramienta para {explicacion}: {comando[0]}.") from exc
    except subprocess.CalledProcessError as exc:
        detalle = (exc.stderr or exc.stdout or "Error desconocido").strip()[-1200:]
        raise RuntimeError(f"No he podido {explicacion}: {detalle}") from exc


def descargar_audio(url: str, carpeta: Path) -> tuple[Path, str | None]:
    import yt_dlp

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": str(carpeta / "original.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
    }
    with yt_dlp.YoutubeDL(opciones) as descarga:
        info = descarga.extract_info(url, download=True)
    candidatos = list(carpeta.glob("original.*"))
    if not candidatos:
        raise RuntimeError("No se ha descargado un archivo de audio.")
    return candidatos[0], info.get("title") if info else None


def duracion_audio(ruta: Path) -> float:
    salida = ejecutar(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(ruta)],
        "averiguar la duración del audio",
    )
    try:
        return float(salida.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("No se ha podido conocer la duración del audio.") from exc


def segmentos_de_groq(audio: Path, inicio_segundos: float, cliente) -> list[tuple[float, str]]:
    with audio.open("rb") as f:
        resultado = cliente.audio.transcriptions.create(
            file=(audio.name, f.read()),
            model=MODELO,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
            temperature=0.0,
        )
    fragmentos = getattr(resultado, "segments", None) or []
    salida: list[tuple[float, str]] = []
    for fragmento in fragmentos:
        if isinstance(fragmento, dict):
            tiempo = fragmento.get("start", 0)
            texto = fragmento.get("text", "")
        else:
            tiempo = getattr(fragmento, "start", 0)
            texto = getattr(fragmento, "text", "")
        if texto:
            salida.append((inicio_segundos + float(tiempo), str(texto)))
    if not salida and getattr(resultado, "text", ""):
        salida = [(inicio_segundos, resultado.text)]
    return salida


def transcribir_con_groq(url: str, carpeta: Path) -> tuple[list[tuple[float, str]], str | None]:
    from groq import Groq

    clave = os.getenv("GROQ_API_KEY", "").strip()
    if not clave or clave == "PEGA_AQUI_TU_CLAVE":
        raise RuntimeError(
            "Falta la clave de Groq. Abre el archivo .env, pega tu clave en GROQ_API_KEY y guarda el archivo."
        )
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("No encuentro FFmpeg/FFprobe. Instálalo y vuelve a abrir la terminal.")
    print("Descargando temporalmente el audio... (si tienes autorización para procesarlo)")
    fuente, titulo = descargar_audio(url, carpeta)
    duracion = duracion_audio(fuente)
    if duracion <= 0:
        raise RuntimeError("La duración del audio no es válida.")
    cliente = Groq(api_key=clave)
    segmentos: list[tuple[float, str]] = []
    total = int((duracion - 0.001) // DURACION_PARTE_SEGUNDOS) + 1
    for indice in range(total):
        inicio = indice * DURACION_PARTE_SEGUNDOS
        parte = carpeta / f"parte_{indice + 1:03d}.mp3"
        print(f"Convirtiendo y transcribiendo parte {indice + 1} de {total}...")
        ejecutar(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(inicio), "-i", str(fuente),
                "-t", str(min(DURACION_PARTE_SEGUNDOS, duracion - inicio)),
                "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "48k",
                str(parte),
            ],
            "convertir el audio a MP3",
        )
        if parte.stat().st_size > 24 * 1024 * 1024:
            raise RuntimeError("Una de las partes supera el límite de subida gratuito de Groq.")
        segmentos.extend(segmentos_de_groq(parte, inicio, cliente))
        parte.unlink(missing_ok=True)
    if not segmentos:
        raise RuntimeError("Groq no ha devuelto palabras reconocibles.")
    return segmentos, titulo


def guardar(url: str, video_id: str, titulo: str, metodo: str, segmentos: list[tuple[float, str]]) -> tuple[Path, Path]:
    RESULTADOS.mkdir(exist_ok=True)
    raiz = f"{nombre_seguro(titulo)}_{video_id}"
    archivo_limpio = RESULTADOS / f"{raiz}_texto.txt"
    archivo_tiempos = RESULTADOS / f"{raiz}_con_tiempos.txt"
    bloques = agrupar_segmentos(segmentos)
    cabecera = (
        f"TÍTULO: {titulo}\nVÍDEO: {url}\n"
        f"FECHA: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"ORIGEN: {metodo}\n"
        "NOTA: La transcripción puede contener errores; confirma términos técnicos con el vídeo.\n\n"
    )
    with archivo_limpio.open("w", encoding="utf-8-sig", newline="\n") as salida:
        salida.write(cabecera)
        for _, texto in bloques:
            salida.write(texto + "\n\n")
    with archivo_tiempos.open("w", encoding="utf-8-sig", newline="\n") as salida:
        salida.write(cabecera)
        for momento, texto in bloques:
            enlace = f"https://www.youtube.com/watch?v={video_id}&t={int(momento)}s"
            salida.write(f"[{marca_tiempo(momento)}] {texto}\n{enlace}\n\n")
    return archivo_limpio, archivo_tiempos


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    entrada = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("Pega el enlace de YouTube: ").strip()
    if not entrada:
        print("No has indicado ningún vídeo.")
        return 2
    try:
        video_id = obtener_id(entrada)
        url = f"https://www.youtube.com/watch?v={video_id}"
        print("Buscando subtítulos disponibles (español o inglés)...")
        try:
            segmentos, metodo = probar_subtitulos(video_id)
            titulo = titulo_oembed(url, video_id)
            print(f"Subtítulos encontrados: {metodo}.")
        except Exception as exc:
            print(f"No se han obtenido subtítulos: {type(exc).__name__}: {exc}")
            if input("¿Descargar el audio temporalmente y enviarlo a Groq? [s/N]: ").lower().strip() not in {"s", "si", "sí"}:
                print("Operación cancelada; no se ha subido ningún audio.")
                return 1
            with tempfile.TemporaryDirectory(prefix="transcriptor_yt_") as carpeta_tmp:
                segmentos, titulo_audio = transcribir_con_groq(url, Path(carpeta_tmp))
            titulo = titulo_audio or titulo_oembed(url, video_id)
            metodo = f"Groq / {MODELO}"
        archivo_limpio, archivo_tiempos = guardar(url, video_id, titulo, metodo, segmentos)
        print(f"\nHECHO. Texto para tus apuntes:\n{archivo_limpio}")
        print(f"Versión con marcas de tiempo y enlaces:\n{archivo_tiempos}")
        return 0
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130
    except Exception as exc:
        print(f"\nERROR: {exc}")
        print("Comprueba el enlace, la conexión, la clave de Groq y que FFmpeg esté instalado.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
