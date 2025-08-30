from django.contrib import admin
from .models import YouTubeDownload

@admin.register(YouTubeDownload)
class YouTubeDownloadAdmin(admin.ModelAdmin):
    list_display = ("youtube_key", "video_format_id", "language", "status", "progress", "post_id", "channel_id")
