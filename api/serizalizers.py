from rest_framework import serializers
from .models import YouTubeVideTask


class YouTubeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouTubeVideTask
        fields = ['id', 'url', 'task_id', 'status', 'created_at']
