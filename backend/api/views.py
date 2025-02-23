from django.shortcuts import render
from rest_framework import generics, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import Todo, Room, UserProfile, UserRole
from .serializers import TodoSerializer, UserSerializer, RoomSerializer, UserProfileSerializer

# Create your views here.

class TodoListCreate(generics.ListCreateAPIView):
    queryset = Todo.objects.all().order_by('-created_at')
    serializer_class = TodoSerializer

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.userprofile.is_admin)

class AuthViewSet(viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=['post'])
    def register(self, request):
        try:
            data = request.data.copy()
            if 'role' not in data:
                data['role'] = UserRole.CUSTOMER
            
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                user = serializer.save()
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user': UserSerializer(user).data,
                    'profile': UserProfileSerializer(user.userprofile).data
                }, status=status.HTTP_201_CREATED)
            print("Validation errors:", serializer.errors)  # Debug için
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print("Register error:", str(e))  # Debug için
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data,
                'profile': UserProfileSerializer(user.userprofile).data
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['get'])
    def me(self, request):
        if request.user.is_authenticated:
            return Response({
                'user': UserSerializer(request.user).data,
                'profile': UserProfileSerializer(request.user.userprofile).data
            })
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Room.objects.all()

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        data['is_participant'] = instance.participants.filter(id=request.user.id).exists() or instance.owner == request.user
        return Response(data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        for room_data in data:
            room = Room.objects.get(id=room_data['id'])
            room_data['is_participant'] = room.participants.filter(id=request.user.id).exists() or room.owner == request.user
        return Response(data)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        room = self.get_object()
        if room.owner == request.user:
            return Response({'error': 'You are the owner of this room'}, status=status.HTTP_400_BAD_REQUEST)
        if room.participants.filter(id=request.user.id).exists():
            return Response({'error': 'You are already a participant'}, status=status.HTTP_400_BAD_REQUEST)
        room.participants.add(request.user)
        return Response({'status': 'joined', 'is_participant': True})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        if room.owner == request.user:
            return Response({'error': 'Owner cannot leave the room'}, status=status.HTTP_400_BAD_REQUEST)
        if not room.participants.filter(id=request.user.id).exists():
            return Response({'error': 'You are not a participant'}, status=status.HTTP_400_BAD_REQUEST)
        room.participants.remove(request.user)
        return Response({'status': 'left', 'is_participant': False})
