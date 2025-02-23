from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthViewSet, RoomViewSet

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'rooms', RoomViewSet, basename='room')

urlpatterns = [
    path('', include(router.urls)),
] 