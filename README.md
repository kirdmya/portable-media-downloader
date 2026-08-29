# Portable Media Downloader

[English](README.md) | [Русский](README.ru.md)

Portable Windows media downloader powered by **yt-dlp**, **Python**, **Deno** and **FFmpeg**.

No system-wide installation of Python, Deno or FFmpeg is required.

![Platform](https://img.shields.io/badge/platform-Windows%20x64-blue)
![License](https://img.shields.io/badge/license-MIT-green)

![Portable Media Downloader](assets/social-preview.png)

## Features

* Download video in MP4
* Download audio as MP3, WAV, M4A or OPUS
* 720p / 1080p / 1440p / 2160p presets
* Download playlists and channels
* Download subtitles, thumbnails and metadata
* Download video fragments
* Browser cookies support
* YouTube fallback strategies
* Portable Python, Deno and FFmpeg
* Download archive for skipping previously downloaded media

## Download

Open the **Releases** page:

https://github.com/kirdmya/portable-media-downloader/releases

Download the latest archive:

```text
PortableMediaDownloader-v1.0.0-win64.zip
```

Extract it anywhere and run:

```text
run.bat
```

That's it.

Python, Deno and FFmpeg do not need to be installed separately.

## Portable

The application keeps its runtime and tools inside the project directory:

```text
PortableMediaDownloader/
├── downloader.py
├── run.bat
├── runtime/
│   └── python/
├── tools/
│   ├── deno/
│   └── ffmpeg/
├── downloads/
└── data/
```

The entire folder can be moved to another directory, disk or compatible Windows x64 computer.

## Build from source

Clone the repository:

```powershell
git clone https://github.com/YOUR_USERNAME/portable-media-downloader.git
cd portable-media-downloader
```

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup_portable.ps1
```

Then start:

```text
run.bat
```

## Updating yt-dlp

Run:

```text
update_python_packages.bat
```

This updates yt-dlp inside the portable Python environment without affecting your system Python.

## YouTube issues

YouTube changes frequently.

If a download suddenly stops working:

1. Update yt-dlp.
2. Make sure Deno is available.
3. Retry the download.
4. Try the built-in fallback or browser cookies options.

Some videos may require additional authentication or PO Token handling.

## Supported websites

Website support is provided by **yt-dlp**, so the application can work with many websites supported by yt-dlp, not only YouTube.

## Disclaimer

Use this application only for content that you are allowed to download.

Users are responsible for complying with applicable laws, copyright rules and website terms of service.

## Credits

Built with:

* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* [Python](https://www.python.org/)
* [Deno](https://deno.com/)
* [FFmpeg](https://ffmpeg.org/)

## License

MIT License.

Third-party components are distributed under their respective licenses.
