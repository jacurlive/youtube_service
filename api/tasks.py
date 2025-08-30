from celery import shared_task
from django.conf import settings
from pyrogram import Client
from .models import YouTubeDownload
import os
import json
import yt_dlp
import random
import subprocess


API_ID = 1626657
API_HASH = "b0d1b4e33de690e1783dfbc547b6c18a"

BOT_TOKEN = "7622544354:AAEvqwts2Pm4A58NoGiJKW1wIUX48GL-Syk"

SESSION_FILE = "/home/jacur/www-projects/youtube_service/api/uploader.session"

CHANNELS = ["@yt_11111", "@yt_22222"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "media", "videos")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

YOUTUBE_LINK = "https://www.youtube.com/watch?v={key}"


def _build_format_string(video_format_id: str, language: str | None, is_audio: bool) -> str:
    if is_audio:
        if language:
            return f"ba[format_note~='(?i){language}'][ext=m4a]/bestaudio[ext=m4a]/bestaudio"
        return "bestaudio[ext=m4a]/bestaudio"
    if language:
        args = (video_format_id, language, video_format_id)
        return "{0}+ba[format_note~='(?i){1}'][ext=m4a]/{2}+140".format(*args)
    return f"{video_format_id}+140"


def _progress_hook_factory(obj_id, total_size, video_size):
    def _hook(d):
        try:
            obj = YouTubeDownload.objects.get(id=obj_id)

            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes") or 0

                if d.get("info_dict", {}).get("vcodec") != "none":
                    progress = int(downloaded / total_size * 100)
                else:
                    progress = int((video_size + downloaded) / total_size * 100)

                obj.progress = min(progress, 99)
                obj.status = "downloading"
                obj.save()

            elif d.get("status") == "finished":
                obj.progress = min(obj.progress + 1, 99)
                obj.save()

        except Exception:
            pass
    return _hook


@shared_task(bind=True)
def download_video_task(self, obj_id):
    try:
        obj = YouTubeDownload.objects.get(id=obj_id)
        obj.status = "downloading"
        obj.progress = 0
        obj.save()

        url = YOUTUBE_LINK.format(key=obj.youtube_key)
        fmt = _build_format_string(obj.video_format_id, obj.language, obj.is_audio)

        ext = "m4a" if obj.is_audio else "mp4"
        output_path = os.path.join(DOWNLOAD_DIR, f"{obj_id}.{ext}")

        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)

            video_fmt = next(
                (f for f in info['formats'] if str(f['format_id']) == obj.video_format_id),
                None
            )
            audio_fmt = next(
                (f for f in info['formats'] if str(f['format_id']) == "140"),
                None
            )

            if not video_fmt:
                raise ValueError(f"Видео формат {obj.video_format_id} не найден в info['formats']")
            if not audio_fmt:
                audio_fmt = next((f for f in info['formats'] if f.get("ext") == "m4a"), None)

            if not audio_fmt:
                raise ValueError("Не найден аудио формат (m4a)")

            video_size = int(video_fmt.get("filesize") or video_fmt.get("filesize_approx") or 0)
            audio_size = int(audio_fmt.get("filesize") or audio_fmt.get("filesize_approx") or 0)
            total_size = video_size + audio_size

        ydl_opts = {
            'format': fmt,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [_progress_hook_factory(obj_id, total_size, video_size)],
        }
        if not obj.is_audio:
            ydl_opts['merge_output_format'] = 'mp4'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        channel_id,post_id = send_to_telegram(output_path)

        obj.status = "success"
        obj.progress = 100
        obj.channel_id = channel_id
        obj.post_id = post_id
        obj.save()

    except Exception as e:
        obj = YouTubeDownload.objects.get(id=obj_id)
        obj.status = "failed"
        obj.progress = 0
        obj.save()
        print(f"Ошибка в задаче {obj_id}: {e}")
        raise e


def get_video_resolution(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    info = json.loads(result.stdout)
    width = info["streams"][0]["width"]
    height = info["streams"][0]["height"]
    return width, height


def send_to_telegram(file_path):
    channel = random.choice(CHANNELS)
    width, height = get_video_resolution(file_path)

    with Client(
        "bot_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    ) as app:
        result = app.send_video(
            chat_id=channel,
            video=file_path,
            caption=os.path.basename(file_path),
            supports_streaming=True,
            width=width,
            height=height
        )

    if os.path.exists(file_path):
        os.remove(file_path)

    return result.chat.id, result.id
