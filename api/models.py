from django.db import models


class YouTubeVideTask(models.Model):
    url = models.URLField()
    task_id = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.url} | {self.status}"


class YouTubeDownload(models.Model):
    youtube_key = models.CharField(max_length=32)
    video_format_id = models.CharField(max_length=10)
    language = models.CharField(max_length=32, null=True, blank=True)
    is_audio = models.BooleanField(default=False)

    task_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, default="pending")
    progress = models.PositiveIntegerField(default=0)
    post_id = models.CharField(max_length=255, null=True, blank=True)
    channel_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('youtube_key', 'video_format_id', 'language', 'is_audio')

    def __str__(self):
        return f"{self.youtube_key} [{self.video_format_id}] lang={self.language} audio={self.is_audio} - {self.status}"
