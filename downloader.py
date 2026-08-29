import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg


# Все пути строятся от расположения этого файла.
# Благодаря этому папку проекта можно переносить целиком.
PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = PROJECT_ROOT / "tools"
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"

PORTABLE_DENO_PATH = TOOLS_DIR / "deno" / ("deno.exe" if os.name == "nt" else "deno")
PORTABLE_FFMPEG_PATH = TOOLS_DIR / "ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")

# В portable-сборке используем локальный ffmpeg.
# Резервный путь через imageio-ffmpeg оставлен для режима разработки.
FFMPEG_PATH = (
    str(PORTABLE_FFMPEG_PATH)
    if PORTABLE_FFMPEG_PATH.is_file()
    else imageio_ffmpeg.get_ffmpeg_exe()
)
ARCHIVE_FILE = DATA_DIR / "yt_dlp_archive.txt"


# ============================================================
# ОКРУЖЕНИЕ / JS RUNTIME
# ============================================================

def existing_executable(candidates):
    for candidate in candidates:
        if not candidate:
            continue
        p = Path(candidate)
        if p.is_file():
            return str(p)
    return None


def find_js_runtime():
    """
    Сначала ищет portable Deno внутри проекта.
    Системные Deno/Node используются только как резервный вариант
    для режима разработки.
    """
    if PORTABLE_DENO_PATH.is_file():
        return "deno", str(PORTABLE_DENO_PATH)

    deno = shutil.which("deno")
    if deno:
        return "deno", deno

    node = shutil.which("node")
    if node:
        return "node", node

    return None, None

def package_installed(package_name):
    try:
        importlib.metadata.version(package_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def environment_report():
    runtime_name, runtime_path = find_js_runtime()

    print("\n" + "=" * 72)
    print("ПРОВЕРКА ОКРУЖЕНИЯ")
    print("=" * 72)

    try:
        ytdlp_version = importlib.metadata.version("yt-dlp")
        print(f"yt-dlp: {ytdlp_version}")
    except importlib.metadata.PackageNotFoundError:
        print("yt-dlp: НЕ НАЙДЕН")

    print(f"FFmpeg: {FFMPEG_PATH}")

    if runtime_name:
        print(f"JS runtime: {runtime_name} -> {runtime_path}")
    else:
        print("JS runtime: НЕ НАЙДЕН")
        print()
        print("Portable Deno не найден:")
        print(f"  {PORTABLE_DENO_PATH}")
        print()
        print("Запусти setup_portable.ps1 из корня проекта.")

    if package_installed("yt-dlp-getpot-wpc"):
        print("PO Token provider WPC: установлен")
    else:
        print("PO Token provider WPC: не установлен")

    print("=" * 72)
    return runtime_name, runtime_path


# ============================================================
# БАЗОВЫЙ ЗАПУСК
# ============================================================

def build_base_command():
    runtime_name, runtime_path = find_js_runtime()

    command = [
        sys.executable,
        "-m",
        "yt_dlp",

        "--ffmpeg-location",
        FFMPEG_PATH,


        "--restrict-filenames",

        "--retries",
        "4",

        "--fragment-retries",
        "8",

        "--retry-sleep",
        "http:linear=1:4:1",

        "--retry-sleep",
        "fragment:linear=1:4:1",
    ]

    # Явно передаём найденный runtime.
    # Это важно, если он установлен, но не виден yt-dlp через PATH.
    if runtime_name and runtime_path:
        command.extend([
            "--js-runtimes",
            f"{runtime_name}:{runtime_path}",
        ])

    return command


def run_command(extra_args, label=None):
    if label:
        print("\n" + "=" * 72)
        print(label)
        print("=" * 72)

    command = [
        *build_base_command(),
        *extra_args,
    ]

    print("\nЗапускаю:")
    print(subprocess.list2cmdline([str(x) for x in command]))
    print()

    try:
        result = subprocess.run(command)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
        raise
    except Exception as exc:
        print(f"\nОшибка запуска: {exc}")
        return False


def run_yt_dlp(args):
    success = run_command(args)

    if success:
        print("\nГотово.")
        print(f"Файлы сохранены в: {DOWNLOADS_DIR}")
    else:
        print("\nОшибка при скачивании.")

    return success


# ============================================================
# ВВОД
# ============================================================

def ask_url():
    return input("Вставь ссылку: ").strip()


def ask_time_range():
    start = input("Начало фрагмента, например 00:01:20: ").strip()
    end = input("Конец фрагмента, например 00:03:45: ").strip()
    return start, end


def ask_browser():
    print()
    print("1) Chrome")
    print("2) Edge")
    print("3) Firefox")
    print("4) Opera")

    choice = input("Выбери браузер: ").strip()

    browsers = {
        "1": "chrome",
        "2": "edge",
        "3": "firefox",
        "4": "opera",
    }

    return browsers.get(choice, "firefox")


def available_cookie_browsers():
    """
    Не тратит время на браузеры, которых явно нет.
    Firefox проверяется первым, т.к. по твоему логу cookies там найдены.
    """
    result = []

    if os.name != "nt":
        return ["firefox", "chrome", "edge", "opera"]

    appdata = Path(os.environ.get("APPDATA", ""))
    local = Path(os.environ.get("LOCALAPPDATA", ""))

    checks = [
        ("firefox", appdata / "Mozilla" / "Firefox"),
        ("chrome", local / "Google" / "Chrome" / "User Data"),
        ("edge", local / "Microsoft" / "Edge" / "User Data"),
        ("opera", appdata / "Opera Software" / "Opera Stable"),
    ]

    for browser, path in checks:
        if path.exists():
            result.append(browser)

    return result


# ============================================================
# FORMAT SELECTORS
# ============================================================

def normal_format(max_height=None):
    if max_height:
        return (
            f"bv*[height<={max_height}]+ba/"
            f"b[height<={max_height}]/"
            f"best[height<={max_height}]"
        )
    return "bv*+ba/b"


def muxed_format(max_height=None):
    if max_height:
        return (
            f"b[height<={max_height}]/"
            f"best[height<={max_height}]/best"
        )
    return "b/best"


def hls_format(max_height=None):
    """
    ВАЖНО: это действительно выбирает m3u8.
    В старой версии fallback назывался HLS, но формат 299+251
    оставался обычным HTTPS.
    """
    if max_height:
        return (
            f"b[protocol^=m3u8][height<={max_height}]/"
            f"best[protocol^=m3u8][height<={max_height}]/"
            f"b[protocol^=m3u8]/"
            f"best[protocol^=m3u8]"
        )

    return (
        "b[protocol^=m3u8]/"
        "best[protocol^=m3u8]"
    )


# ============================================================
# FALLBACK ENGINE
# ============================================================

def try_browser_cookies(
    url,
    output_path,
    max_height=None,
    extra_args=None,
):
    if extra_args is None:
        extra_args = []

    browsers = available_cookie_browsers()

    if not browsers:
        print("\nНе найден ни один профиль браузера с cookies.")
        return False

    for browser in browsers:
        # Cookies не используем для HLS fallback: YouTube может выдавать
        # другой набор форматов при авторизованной сессии.
        args = [
            "--cookies-from-browser",
            browser,

            "--extractor-args",
            "youtube:player_client=default,web_embedded",

            "--no-continue",

            "-f",
            normal_format(max_height),

            "--merge-output-format",
            "mp4",

            *extra_args,

            "-o",
            str(output_path),

            url,
        ]

        if run_command(
            args,
            label=f"FALLBACK COOKIES: {browser}",
        ):
            print(f"\nУСПЕХ через cookies из {browser}.")
            return True

    return False


def try_mweb_po_provider(
    url,
    output_path,
    max_height=None,
    extra_args=None,
):
    """
    Если установлен yt-dlp-getpot-wpc, yt-dlp сам запрашивает PO Token.
    """
    if not package_installed("yt-dlp-getpot-wpc"):
        return False

    if extra_args is None:
        extra_args = []

    args = [
        "--extractor-args",
        "youtube:player_client=mweb",

        "--no-continue",

        "-f",
        normal_format(max_height),

        "--merge-output-format",
        "mp4",

        *extra_args,

        "-o",
        str(output_path),

        url,
    ]

    return run_command(
        args,
        label="FALLBACK: mweb + автоматический PO Token provider",
    )


def download_video_auto(
    url,
    output_path,
    max_height=None,
    cookies_fallback=True,
    extra_args=None,
):
    if extra_args is None:
        extra_args = []

    runtime_name, runtime_path = find_js_runtime()

    # Не скрываем главную проблему за десятком одинаковых 403.
    if not runtime_name:
        print()
        print("ВНИМАНИЕ: JavaScript runtime не найден.")
        print("YouTube сейчас требует его для JS challenge.")
        print("Скрипт всё равно попробует способы, которые иногда работают,")
        print("но вероятность 403 значительно выше.")
        print()

    strategies = [
        {
            "name": "1. Default / обычные форматы",
            "args": [
                "-f",
                normal_format(max_height),
                "--merge-output-format",
                "mp4",
            ],
        },

        {
            "name": "2. Android VR",
            "args": [
                "--extractor-args",
                "youtube:player_client=android_vr",

                "--no-continue",

                "-f",
                normal_format(max_height),

                "--merge-output-format",
                "mp4",
            ],
        },

        {
            "name": "3. Web Embedded",
            "args": [
                "--extractor-args",
                "youtube:player_client=web_embedded",

                "--no-continue",

                "-f",
                normal_format(max_height),

                "--merge-output-format",
                "mp4",
            ],
        },

        {
            # Реальный HLS selector, а не обычный 299+251.
            "name": "4. Web Safari HLS / m3u8",
            "args": [
                "--extractor-args",
                "youtube:player_client=web_safari",

                "--no-continue",

                "-f",
                hls_format(max_height),

                "--merge-output-format",
                "mp4",
            ],
        },

        {
            "name": "5. Единый muxed-поток",
            "args": [
                "--no-continue",

                "-f",
                muxed_format(max_height),

                "--merge-output-format",
                "mp4",
            ],
        },

        {
            # Иногда помогает, когда CDN плохо переносит большой range.
            # Это не замена PO Token, а дополнительный сетевой fallback.
            "name": "6. HTTP chunks",
            "args": [
                "--no-continue",

                "--http-chunk-size",
                "10M",

                "-f",
                normal_format(max_height),

                "--merge-output-format",
                "mp4",
            ],
        },
    ]

    total = len(strategies)

    for index, strategy in enumerate(strategies, 1):
        args = [
            *strategy["args"],
            *extra_args,
            "-o",
            str(output_path),
            url,
        ]

        if run_command(
            args,
            label=f"Попытка {index}/{total}: {strategy['name']}",
        ):
            print()
            print(f"УСПЕХ: {strategy['name']}")
            print(f"Файлы сохранены в: {DOWNLOADS_DIR}")
            return True

        print("\nНе сработало. Переключаюсь...")

    # В 2026 году это рекомендуемый путь yt-dlp, если provider установлен.
    if try_mweb_po_provider(
        url,
        output_path,
        max_height=max_height,
        extra_args=extra_args,
    ):
        print("\nУСПЕХ: mweb + PO Token.")
        print(f"Файлы сохранены в: {DOWNLOADS_DIR}")
        return True

    if cookies_fallback:
        if try_browser_cookies(
            url,
            output_path,
            max_height=max_height,
            extra_args=extra_args,
        ):
            print(f"Файлы сохранены в: {DOWNLOADS_DIR}")
            return True

    print("\n" + "=" * 72)
    print("ВСЕ СПОСОБЫ ЗАВЕРШИЛИСЬ ОШИБКОЙ")
    print("=" * 72)

    if not runtime_name:
        print()
        print("Главная проблема этой машины:")
        print("  JS runtime НЕ установлен/не найден.")
        print()
        print("В PowerShell из папки проекта:")
        print(r"  .\setup_portable.ps1")
        print()
        print(r"Deno будет установлен локально в tools\deno.")
        print()

    if not package_installed("yt-dlp-getpot-wpc"):
        print("Если после установки Deno 403 останется, следующий уровень:")
        print("  python -m pip install -U yt-dlp-getpot-wpc")
        print()
        print("Для WPC нужен Chrome/Chromium. Provider сам откроет браузер")
        print("для получения PO Token на нужное видео.")

    return False


# ============================================================
# ВИДЕО
# ============================================================

def download_video_mp4(url):
    output_path = DOWNLOADS_DIR / "video_mp4" / "%(title)s.%(ext)s"
    download_video_auto(url, output_path)


def download_playlist_mp4(url):
    output_path = (
        DOWNLOADS_DIR
        / "playlists_mp4"
        / "%(playlist_title)s"
        / "%(playlist_index)03d - %(title)s.%(ext)s"
    )

    download_video_auto(
        url,
        output_path,
        extra_args=["--yes-playlist"],
    )


def download_video_mp4_720p(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_mp4_720p" / "%(title)s.%(ext)s",
        max_height=720,
    )


def download_video_mp4_1080p(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_mp4_1080p" / "%(title)s.%(ext)s",
        max_height=1080,
    )


def download_video_mp4_2k(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_mp4_2k_1440p" / "%(title)s.%(ext)s",
        max_height=1440,
    )


def download_video_mp4_4k(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_mp4_4k_2160p" / "%(title)s.%(ext)s",
        max_height=2160,
    )


def download_video_best(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_best" / "%(title)s.%(ext)s",
    )


def download_video_only(url):
    run_yt_dlp([
        "-f",
        "bv*/bestvideo/best",
        "-o",
        str(DOWNLOADS_DIR / "video_only" / "%(title)s.%(ext)s"),
        url,
    ])


# ============================================================
# АУДИО
# ============================================================

def download_audio_mp3(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", str(DOWNLOADS_DIR / "audio_mp3" / "%(title)s.%(ext)s"),
        url,
    ])


def download_audio_wav(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "wav",
        "-o", str(DOWNLOADS_DIR / "audio_wav" / "%(title)s.%(ext)s"),
        url,
    ])


def download_audio_original(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-o", str(DOWNLOADS_DIR / "audio_original" / "%(title)s.%(ext)s"),
        url,
    ])


def download_audio_m4a(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "m4a",
        "--audio-quality", "0",
        "-o", str(DOWNLOADS_DIR / "audio_m4a" / "%(title)s.%(ext)s"),
        url,
    ])


def download_audio_opus(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "opus",
        "--audio-quality", "0",
        "-o", str(DOWNLOADS_DIR / "audio_opus" / "%(title)s.%(ext)s"),
        url,
    ])


# ============================================================
# СУБТИТРЫ / ОБЛОЖКИ / МЕТАДАННЫЕ
# ============================================================

def download_subtitles_only(url):
    run_yt_dlp([
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", "ru,en",
        "--convert-subs", "srt",
        "-o", str(DOWNLOADS_DIR / "subtitles" / "%(title)s.%(ext)s"),
        url,
    ])


def download_video_with_subtitles(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_with_subtitles" / "%(title)s.%(ext)s",
        extra_args=[
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "ru,en",
            "--convert-subs", "srt",
        ],
    )


def download_thumbnail(url):
    run_yt_dlp([
        "--skip-download",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "-o", str(DOWNLOADS_DIR / "thumbnails" / "%(title)s.%(ext)s"),
        url,
    ])


def download_metadata_json(url):
    run_yt_dlp([
        "--skip-download",
        "--write-info-json",
        "-o", str(DOWNLOADS_DIR / "metadata_json" / "%(title)s.%(ext)s"),
        url,
    ])


def download_video_with_thumbnail_and_metadata(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_archive" / "%(title)s.%(ext)s",
        extra_args=[
            "--write-thumbnail",
            "--convert-thumbnails", "jpg",
            "--write-info-json",
            "--embed-metadata",
            "--embed-thumbnail",
        ],
    )


# ============================================================
# ФРАГМЕНТЫ / ПЛЕЙЛИСТЫ / КАНАЛЫ
# ============================================================

def download_video_fragment(url):
    start, end = ask_time_range()

    download_video_auto(
        url,
        DOWNLOADS_DIR / "video_fragments" / "%(title)s - fragment.%(ext)s",
        extra_args=[
            "--download-sections",
            f"*{start}-{end}",
        ],
    )


def download_playlist_mp3(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--yes-playlist",
        "-o",
        str(
            DOWNLOADS_DIR
            / "playlists_mp3"
            / "%(playlist_title)s"
            / "%(playlist_index)03d - %(title)s.%(ext)s"
        ),
        url,
    ])


def download_playlist_wav(url):
    run_yt_dlp([
        "-f", "ba/bestaudio/best",
        "-x",
        "--audio-format", "wav",
        "--yes-playlist",
        "-o",
        str(
            DOWNLOADS_DIR
            / "playlists_wav"
            / "%(playlist_title)s"
            / "%(playlist_index)03d - %(title)s.%(ext)s"
        ),
        url,
    ])


def download_channel(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR
        / "channels"
        / "%(channel)s"
        / "%(upload_date)s - %(title)s.%(ext)s",
        extra_args=["--yes-playlist"],
    )


def download_only_new(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR / "only_new" / "%(title)s.%(ext)s",
        extra_args=[
            "--download-archive",
            str(ARCHIVE_FILE),
        ],
    )


# ============================================================
# РУЧНОЙ РЕЖИМ COOKIES
# ============================================================

def download_with_cookies(url):
    browser = ask_browser()

    output_path = (
        DOWNLOADS_DIR
        / "with_cookies"
        / "%(title)s.%(ext)s"
    )

    strategies = [
        [
            "--cookies-from-browser", browser,
            "--extractor-args",
            "youtube:player_client=default,web_embedded",
            "--no-continue",
            "-f", "bv*+ba/b",
            "--merge-output-format", "mp4",
        ],
        [
            "--cookies-from-browser", browser,
            "--no-continue",
            "-f", "b/best",
            "--merge-output-format", "mp4",
        ],
    ]

    for index, strategy in enumerate(strategies, 1):
        if run_command(
            [
                *strategy,
                "-o", str(output_path),
                url,
            ],
            label=f"Cookies попытка {index}/{len(strategies)}",
        ):
            print("\nГотово.")
            print(f"Файлы сохранены в: {DOWNLOADS_DIR}")
            return

    print("\nВсе варианты с cookies завершились ошибкой.")


# ============================================================
# SHORTS / REELS / TIKTOK
# ============================================================

def download_shorts_reels_tiktok(url):
    download_video_auto(
        url,
        DOWNLOADS_DIR
        / "shorts_reels_tiktok"
        / "%(title)s.%(ext)s",
    )


# ============================================================
# ФОРМАТЫ / ДИАГНОСТИКА
# ============================================================

def list_formats(url):
    run_yt_dlp([
        "-F",
        url,
    ])


def verbose_diagnostics(url):
    run_yt_dlp([
        "-vU",
        "-F",
        url,
    ])


# ============================================================
# МЕНЮ
# ============================================================

def main():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    environment_report()

    print()
    print("YT-DLP Downloader")
    print()
    print("1) Скачать видео в MP4 (AUTO FALLBACK)")
    print("2) Скачать только аудио в MP3")
    print("3) Скачать только аудио в WAV")
    print("4) Скачать плейлист в MP4")
    print("5) Скачать видео MP4 720p")
    print("6) Скачать видео MP4 1080p")
    print("7) Скачать видео MP4 2K / 1440p")
    print("8) Скачать видео MP4 4K / 2160p")
    print("9) Скачать видео в лучшем доступном качестве")
    print("10) Скачать только видео без аудио")
    print("11) Скачать только аудио без конвертации")
    print("12) Скачать аудио M4A")
    print("13) Скачать аудио OPUS")
    print("14) Скачать только субтитры RU/EN")
    print("15) Скачать видео вместе с субтитрами RU/EN")
    print("16) Скачать превью / обложку")
    print("17) Скачать метаданные JSON")
    print("18) Скачать видео + обложку + метаданные")
    print("19) Скачать фрагмент видео")
    print("20) Скачать плейлист в MP3")
    print("21) Скачать плейлист в WAV")
    print("22) Скачать канал целиком")
    print("23) Скачать только новые видео без повторов")
    print("24) Скачать вручную с cookies")
    print("25) Скачать Shorts / Reels / TikTok")
    print("26) Показать доступные форматы")
    print("27) Полная диагностика -vU")
    print()

    choice = input("Выбери сценарий: ").strip()
    url = ask_url()

    if not url:
        print("Ссылка не указана.")
        return

    actions = {
        "1": download_video_mp4,
        "2": download_audio_mp3,
        "3": download_audio_wav,
        "4": download_playlist_mp4,
        "5": download_video_mp4_720p,
        "6": download_video_mp4_1080p,
        "7": download_video_mp4_2k,
        "8": download_video_mp4_4k,
        "9": download_video_best,
        "10": download_video_only,
        "11": download_audio_original,
        "12": download_audio_m4a,
        "13": download_audio_opus,
        "14": download_subtitles_only,
        "15": download_video_with_subtitles,
        "16": download_thumbnail,
        "17": download_metadata_json,
        "18": download_video_with_thumbnail_and_metadata,
        "19": download_video_fragment,
        "20": download_playlist_mp3,
        "21": download_playlist_wav,
        "22": download_channel,
        "23": download_only_new,
        "24": download_with_cookies,
        "25": download_shorts_reels_tiktok,
        "26": list_formats,
        "27": verbose_diagnostics,
    }

    action = actions.get(choice)

    if action:
        action(url)
    else:
        print("Неверный вариант.")


if __name__ == "__main__":
    main()
