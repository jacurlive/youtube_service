import requests
import os
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from django.shortcuts import get_object_or_404

from dotenv import load_dotenv

from .models import YouTubeDownload
from .tasks import download_video_task

load_dotenv()

GET_INFO_API = os.environ['GET_INFO_API']


class YouTubeInfoRequestAPIView(APIView):
    def post(self, request):
        url = request.data.get('url')

        if not url:
            return Response({'error': 'No URL provided'}, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            api_response = requests.post(f"{GET_INFO_API}video/", json={'url': url})
            api_data = api_response.json()
        except Exception as e:
            return Response({'error': f'Failed to request INFO API: {e}'}, status=drf_status.HTTP_502_BAD_GATEWAY)

        task_id = api_data.get('task_id')
        if not task_id:
            return Response({'error': 'No task_id returned from INFO API'}, status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR)

        start_time = time.time()
        while True:
            try:
                task_resp = requests.get(f"{GET_INFO_API}status/{task_id}")
                task_data = task_resp.json()
            except Exception as e:
                return Response({'error': f'Failed to request task status: {e}'}, status=drf_status.HTTP_502_BAD_GATEWAY)

            status_ = task_data.get("status")
            if status_ in ["success", "fail"]:
                return Response(task_data)

            if time.time() - start_time > 20:
                return Response({'error': 'Timeout waiting for task'}, status=drf_status.HTTP_504_GATEWAY_TIMEOUT)

            time.sleep(1)


class YouTubeDownloadAPIView(APIView):
    def post(self, request):
        youtube_key = request.data.get("youtube_key")
        video_format_id = request.data.get("video_format_id")
        language = request.data.get("language")
        is_audio = request.data.get("is_audio")

        if isinstance(is_audio, str):
            is_audio = is_audio.lower() in ["1", "true", "yes"]

        if not all([youtube_key, video_format_id]):
            return Response({"error": "Missing required fields"}, status=drf_status.HTTP_400_BAD_REQUEST)

        existing = YouTubeDownload.objects.filter(
            youtube_key=youtube_key,
            video_format_id=video_format_id,
            language=language,
            is_audio=is_audio,
            status="success"
        ).first()

        if existing:
            return Response({
                "status": "success",
                "channel_id": existing.channel_id,
                "post_id": existing.post_id
            })

        obj, created = YouTubeDownload.objects.get_or_create(
            youtube_key=youtube_key,
            video_format_id=video_format_id,
            language=language,
            is_audio=is_audio or False,
            defaults={"status": "pending"}
        )

        task = download_video_task.delay(obj.id)
        obj.task_id = task.id
        obj.save()

        return Response({
            "status": "pending",
            "task_id": obj.task_id
        })


class YouTubeStatusAPIView(APIView):
    def get(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response({"error": "task_id is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        obj = get_object_or_404(YouTubeDownload, task_id=task_id)

        return Response({
            "status": obj.status,
            "progress": obj.progress,
            "channel_id": obj.channel_id,
            "post_id": obj.post_id
        })


class GetFilesAPIView(APIView):
    def get(self, request):
        youtube_key = request.query_params.get("youtube_key")
        if not youtube_key:
            return Response({"error": "youtube_key is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        files = YouTubeDownload.objects.filter(youtube_key=youtube_key, status="success").values(
            "channel_id", "post_id", "video_format_id", "language"
        )

        return Response(list(files))


class GetFileAPIView(APIView):
    def get(self, request):
        youtube_key = request.query_params.get("youtube_key")
        f_quality = request.query_params.get("f_quality")   # это video_format_id
        language = request.query_params.get("language")

        if not all([youtube_key, f_quality]):
            return Response(
                {"error": "youtube_key and f_quality are required"},
                status=drf_status.HTTP_400_BAD_REQUEST
            )

        filters = {
            "youtube_key": youtube_key,
            "video_format_id": f_quality,
            "status": "success"
        }

        if language:
            filters["language"] = language
        else:
            filters["language__isnull"] = True

        obj = get_object_or_404(YouTubeDownload, **filters)

        return Response({
            "channel_id": obj.channel_id,
            "message_id": obj.post_id,
            "f_quality": obj.video_format_id,
            "language": obj.language
        })


class GetFilesCountAPIView(APIView):
    def get(self, request):
        f_quality = request.query_params.get("f_quality")

        if f_quality:
            count = YouTubeDownload.objects.filter(video_format_id=f_quality, status="success").count()
        else:
            count = YouTubeDownload.objects.filter(status="success").count()

        return Response({"count": count})


class SaveFileAPIView(APIView):
    def post(self, request):
        youtube_key = request.data.get("youtube_key")
        channel_id = request.data.get("channel_id")
        message_id = request.data.get("message_id")
        f_quality = request.data.get("f_quality")
        language = request.data.get("language")

        if not all([youtube_key, channel_id, message_id, f_quality]):
            return Response({"error": "Missing required fields"}, status=drf_status.HTTP_400_BAD_REQUEST)

        obj, created = YouTubeDownload.objects.update_or_create(
            youtube_key=youtube_key,
            video_format_id=f_quality,
            language=language,
            is_audio=False,
            defaults={
                "status": "success",
                "channel_id": channel_id,
                "post_id": message_id
            }
        )

        return Response({
            "created": created,
            "channel_id": obj.channel_id,
            "message_id": obj.post_id,
            "f_quality": obj.video_format_id,
            "language": obj.language
        })


class DeleteFileAPIView(APIView):
    def delete(self, request):
        youtube_key = request.data.get("youtube_key")
        f_quality = request.data.get("f_quality")
        language = request.data.get("language")

        if not all([youtube_key, f_quality]):
            return Response({"error": "youtube_key and f_quality are required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        obj = get_object_or_404(
            YouTubeDownload,
            youtube_key=youtube_key,
            video_format_id=f_quality,
            language=language
        )

        obj.delete()
        return Response({"status": "deleted"})
