from django.urls import path
from .views import (
    YouTubeInfoRequestAPIView, 
    YouTubeDownloadAPIView, 
    YouTubeStatusAPIView,
    GetFilesAPIView,
    GetFileAPIView,
    GetFilesCountAPIView,
    SaveFileAPIView,
    DeleteFileAPIView
)


urlpatterns = [
    path('youtube/request', YouTubeInfoRequestAPIView.as_view()),
    path('youtube/download', YouTubeDownloadAPIView.as_view()),
    path('youtube/status', YouTubeStatusAPIView.as_view()),
    path("get_files/", GetFilesAPIView.as_view()),
    path("get_file/", GetFileAPIView.as_view()),
    path("get_files_count/", GetFilesCountAPIView.as_view()),
    path("save_file/", SaveFileAPIView.as_view()),
    path("delete_file/", DeleteFileAPIView.as_view()),
]
