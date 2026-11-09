# Transcriptor de YouTube para apuntes

Herramienta de línea de comandos que convierte el contenido hablado de **un vídeo de YouTube** en archivos de texto para consultar, organizar y redactar apuntes.

Su objetivo es sencillo: **pegar un enlace y obtener una transcripción legible**, sin montar una aplicación web ni necesitar un ordenador con una GPU potente.

El programa utiliza un enfoque híbrido:

1. **Primero intenta recuperar los subtítulos disponibles de YouTube**, priorizando el español y, después, el inglés.
2. **Si no consigue obtenerlos**, pregunta si deseas descargar temporalmente el audio y enviarlo a **Groq** para transcribirlo con **Whisper Large V3 Turbo**.
3. Guarda **dos archivos `.txt`**: uno limpio para trabajar con tus apuntes y otro con marcas de tiempo y enlaces para consultar los fragmentos originales del vídeo.

> **Aviso:** se trata de un proyecto de uso personal. Puede fallar con vídeos restringidos y las transcripciones, especialmente las automáticas, deben revisarse si contienen nombres propios o términos técnicos.

## Características

- Compatible con vídeos en **español e inglés** (no realiza traducción automática).
- Admite enlaces `youtube.com/watch`, `youtu.be`, `youtube.com/shorts`, `youtube.com/live` y `youtube.com/embed`.
- Aprovecha los subtítulos existentes **sin recurrir a la API de Groq** cuando estos son accesibles.
- Utiliza **Whisper Large V3 Turbo a través de Groq** como alternativa, sin ejecutar el modelo en tu ordenador.
- Solicita **confirmación explícita** antes de descargar y enviar audio a Groq.
- Divide automáticamente el audio largo en partes de **hasta 25 minutos**, lo convierte a MP3 mono y comprueba el tamaño de cada parte antes de enviarla.
- Genera texto agrupado en párrafos y una versión con marcas de tiempo enlazadas al vídeo.
- Elimina los archivos de audio temporales cuando termina el proceso (también si se produce un error dentro de la carpeta temporal).
- Funciona en Windows con dos archivos `.bat` para facilitar la instalación y el uso.

## ¿Cómo funciona?

```text
URL de YouTube
      |
      v
Validar enlace y extraer ID del vídeo
      |
      v
Intentar recuperar subtítulos (es -> en)
      |
      +---- Disponibles ------> Agrupar texto y conservar tiempos
      |
      +---- No disponibles ---> Solicitar permiso al usuario
                                    |
                                    v
                              Descargar audio con yt-dlp
                                    |
                                    v
                              Convertir y dividir con FFmpeg
                                    |
                                    v
                              Groq / Whisper Large V3 Turbo
                                    |
                                    v
                              Agrupar texto y conservar tiempos
      |
      v
Guardar 2 archivos TXT en transcripciones/
```

**Importante:** si YouTube bloquea la consulta de subtítulos, el programa puede ofrecer la alternativa de Groq, pero eso **no garantiza** que sea posible acceder al audio. Si no hay subtítulos ni audio accesibles, la transcripción no podrá completarse.

## Requisitos

- **Windows 10 u 11** para utilizar los lanzadores `.bat` (el script Python también puede ejecutarse en otros sistemas compatibles).
- **Python 3** con soporte para entornos virtuales; se recomienda **Python 3.13**.
- **Conexión a Internet**.
- **FFmpeg y FFprobe** para la vía de audio con Groq. No son necesarios cuando se recuperan subtítulos directamente.
- **Clave de API de Groq**, únicamente cuando necesites la transcripción por IA.

No hace falta instalar Whisper localmente ni disponer de tarjeta gráfica dedicada.

## Instalación en Windows

### 1. Instalar Python

Abre **PowerShell** y ejecuta:

```powershell
winget install -e --id Python.Python.3.13
```

Cierra y abre otra vez PowerShell. Verifica la instalación:

```powershell
py --version
```

Si `py` no se reconoce, revisa que Python y el *Python Launcher* estén instalados correctamente. También puedes obtener Python en <https://www.python.org/downloads/>.

### 2. Instalar FFmpeg

En PowerShell:

```powershell
winget install -e --id Gyan.FFmpeg
```

Reabre la terminal y comprueba:

```powershell
ffmpeg -version
ffprobe -version
```

Este paso es imprescindible **solo** si vas a transcribir audio con Groq.

### 3. Descargar el proyecto e instalar dependencias

Descarga el código de este repositorio (botón **Code > Download ZIP**) y descomprímelo en una carpeta, o clónalo con Git:

```powershell
git clone URL_DE_TU_REPOSITORIO
```

Accede a la carpeta del proyecto y haz doble clic en:

```text
1_INSTALAR.bat
```

El instalador:

1. Crea un entorno virtual de Python llamado `.venv`.
2. Actualiza `pip` dentro de ese entorno.
3. Instala las librerías indicadas en `requirements.txt`.
4. Si todavía no existe, crea `.env` a partir de `.env.example`.

No es necesario activar el entorno virtual manualmente para usar los `.bat`.

### 4. Configurar la API de Groq (opcional)

Si quieres poder transcribir vídeos cuyos subtítulos no sean accesibles:

1. Accede a <https://console.groq.com/keys>.
2. Crea una clave de API.
3. Abre el archivo `.env` de la carpeta del proyecto con un editor de texto.
4. Sustituye el valor de ejemplo por tu clave:

```dotenv
GROQ_API_KEY=TU_CLAVE_REAL
```

5. Guarda el archivo.

Si únicamente vas a utilizar subtítulos existentes, puedes omitir este paso.

> **Seguridad:** nunca publiques tu clave. El archivo `.env` está excluido del repositorio mediante `.gitignore`. Asegúrate también de no pegarla en capturas de pantalla, incidencias o registros compartidos.

## Uso

### Opción sencilla: doble clic

Ejecuta:

```text
2_TRANSCRIBIR.bat
```

Cuando aparezca el mensaje, pega la URL de un vídeo de YouTube:

```text
Pega el enlace de YouTube: https://www.youtube.com/watch?v=XXXXXXXXXXX
```

- Si hay subtítulos accesibles, los procesa directamente.
- Si no los hay, pregunta `¿Descargar el audio temporalmente y enviarlo a Groq? [s/N]:`.
  - Escribe `s` para autorizarlo, siempre que tengas derecho a procesar ese contenido.
  - Pulsa **Intro** o escribe `n` para cancelar sin enviar audio.

Al terminar, el programa muestra las rutas de los dos archivos generados.

### Opción desde la terminal

Desde PowerShell, en la carpeta del proyecto:

```powershell
.\.venv\Scripts\python.exe .\transcribir.py "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

Si ejecutas el script sin URL, te pedirá que la introduzcas.

## Archivos de salida

Los resultados se guardan en la carpeta `transcripciones/`, que se crea automáticamente:

```text
transcripciones/
├── Nombre del video_XXXXXXXXXXX_texto.txt
└── Nombre del video_XXXXXXXXXXX_con_tiempos.txt
```

Ambos archivos incluyen una cabecera con el título, el enlace original, la fecha, el método empleado y una advertencia sobre posibles errores de transcripción.

**1. Archivo `_texto.txt`**

Contiene párrafos sin marcas de tiempo intercaladas, pensado para copiar su contenido y utilizarlo como base al redactar apuntes.

**2. Archivo `_con_tiempos.txt`**

Incluye marcas de tiempo y enlaces al segundo correspondiente del vídeo:

```text
[02:15] Los modelos de lenguaje permiten trabajar con información...
https://www.youtube.com/watch?v=XXXXXXXXXXX&t=135s
```

Los archivos se escriben en **UTF-8 con BOM** para facilitar su apertura en aplicaciones de Windows. Si vuelves a procesar el **mismo vídeo**, los nombres de salida serán los mismos y los archivos existentes pueden sobrescribirse.

## Estructura del proyecto

```text
Transcriptor_YT_Whisper/
├── transcribir.py           # Programa principal
├── requirements.txt        # Dependencias de Python
├── .env.example             # Ejemplo de configuración de Groq
├── .gitignore               # Excluye secretos y archivos generados
├── 1_INSTALAR.bat           # Preparación automática en Windows
├── 2_TRANSCRIBIR.bat       # Ejecución sencilla en Windows
├── LEEME.txt                # Instrucciones rápidas originales
├── README.md                # Documentación para GitHub
├── .env                     # Configuración privada (se crea localmente)
├── .venv/                   # Entorno virtual (se crea localmente)
└── transcripciones/         # Salidas (se crea al usar la herramienta)
```

Los tres últimos elementos se generan localmente y **no deben subirse a GitHub**.

### Dependencias principales

| Componente | Función |
| --- | --- |
| [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api) | Obtiene subtítulos accesibles de YouTube. |
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | Descarga temporalmente el audio cuando se acepta usar Groq. |
| [FFmpeg](https://ffmpeg.org/) / FFprobe | Calcula duración, convierte y fragmenta el audio. |
| [Groq SDK](https://console.groq.com/docs/speech-to-text) | Envía el audio al servicio de transcripción con Whisper. |
| [`python-dotenv`](https://github.com/theskumar/python-dotenv) | Carga `GROQ_API_KEY` desde `.env`. |

La versión concreta de las bibliotecas se resuelve durante la instalación, según los rangos declarados en `requirements.txt`.

## Privacidad, límites y coste

- **Subtítulos de YouTube:** el programa consulta YouTube para recuperar los subtítulos. No envía audio a Groq en esta vía.
- **Transcripción mediante Groq:** cuando autorizas la alternativa por IA, el programa descarga audio temporalmente y envía sus fragmentos a la infraestructura de Groq. Revisa las condiciones de tratamiento de datos de ese servicio antes de utilizar material confidencial.
- **Archivos locales:** las transcripciones se almacenan en tu equipo; el audio descargado para el procesamiento se guarda en una carpeta temporal que se elimina al finalizar.
- **Límites de la API:** Groq tiene cuotas y límites de tamaño que dependen del plan. El programa comprime y comprueba cada fragmento antes de enviarlo, pero eso no evita posibles errores por cuotas, disponibilidad o cambios en la API. Consulta las condiciones vigentes en [Groq](https://console.groq.com/docs/speech-to-text).
- **Precisión:** la transcripción no garantiza fidelidad absoluta. Comprueba nombres de personas, herramientas, versiones, cifras y explicaciones técnicas con el vídeo.
- **Idiomas:** prioriza subtítulos en español (`es`) y después inglés (`en`). Whisper mantiene el idioma hablado en lugar de traducirlo.
- **Restricciones de YouTube:** algunos vídeos bloquean la recuperación de subtítulos o la descarga de audio. Respeta los derechos de autor y las condiciones del servicio; poder descargar un contenido técnicamente no implica estar autorizado a hacerlo.

## Solución de problemas

| Problema | Qué comprobar o hacer |
| --- | --- |
| `"cho"`, `"y"` o `"f"` no se reconoce como un comando | Estás utilizando una versión antigua de los `.bat` con saltos de línea incorrectos. Sustituye **ambos** archivos por los corregidos, con formato **CRLF** de Windows. |
| `No se ha podido crear el entorno` | Ejecuta `py --version` y, si falla, reinstala Python con el Launcher. Vuelve a abrir la terminal. |
| `ffmpeg` / `ffprobe` no reconocido | Instala FFmpeg y reabre PowerShell para actualizar el `PATH`. |
| `Falta la clave de Groq` | Revisa que exista `.env` junto a `transcribir.py` y que `GROQ_API_KEY` tenga una clave real. |
| Error HTTP `429` | Se ha alcanzado un límite de la API. Consulta el uso y las cuotas de tu cuenta de Groq. |
| No encuentra subtítulos | El programa debería ofrecer Groq como alternativa, aunque descargar el audio también puede estar bloqueado. |
| Error al descargar audio | Actualiza `yt-dlp` y verifica que el vídeo sea accesible y que tengas autorización para procesarlo. |
| Texto con errores técnicos | Contrasta los fragmentos dudosos con el vídeo usando el archivo `_con_tiempos.txt`. |

Para actualizar `yt-dlp` desde PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade yt-dlp
```

## Decisiones de diseño y evolución

Este proyecto partió de la idea de transcribir vídeos con Whisper, tomando como referencia [un ejemplo sencillo de midudev](https://gist.github.com/midudev/2bc13e6ef38ccc4716fba8b7258f1403). Se decidió **no copiar literalmente ese enfoque** por varias razones:

- Evitar la dependencia de `pytube` y preferir `yt-dlp` para la vía de descarga de audio.
- **No ejecutar Whisper localmente:** utilizar la API de Groq para reducir la carga del ordenador.
- **Evitar transcripciones innecesarias:** intentar primero los subtítulos de YouTube.
- Conservar **marcas de tiempo** para revisar lo dicho en el vídeo.
- Guardar resultados en archivos reutilizables, en lugar de limitarse a imprimirlos en pantalla.
- Solicitar consentimiento antes de enviar audio a un servicio externo.

### Corrección aplicada a los instaladores

En la primera versión, los lanzadores de Windows tenían saltos de línea incompatibles con `cmd.exe`, lo que provocaba errores como `"cho" no se reconoce como un comando`. Los archivos `1_INSTALAR.bat` y `2_TRANSCRIBIR.bat` se corrigieron para utilizar **CRLF**, el formato adecuado para ejecutarlos como archivos por lotes en Windows.

### Alcance actual

Esta versión está diseñada para **un vídeo cada vez** y para generar archivos de texto de apoyo. **No incluye** interfaz web, base de datos, resumen automático, traducción, procesamiento de listas de reproducción ni separación de hablantes. Si algún día se añaden, serán mejoras futuras, no funciones disponibles ahora.