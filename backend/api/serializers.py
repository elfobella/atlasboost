from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Todo, Room, UserProfile, UserRole, Message

class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = ['id', 'title', 'completed', 'created_at']

class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('id', 'username', 'email', 'role', 'created_at')

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.CUSTOMER, write_only=True)
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'role', 'profile')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': False}
        }

    def validate_role(self, value):
        if value not in [choice[0] for choice in UserRole.choices]:
            raise serializers.ValidationError(f"Invalid role. Choices are: {', '.join([choice[0] for choice in UserRole.choices])}")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', UserRole.CUSTOMER)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        UserProfile.objects.create(user=user, role=role)
        return user

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'content', 'sender_username', 'timestamp')

class RoomSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    participants_count = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ('id', 'name', 'created_at', 'owner', 'owner_username', 'participants_count', 'messages')
        read_only_fields = ('owner',)

    def get_participants_count(self, obj):
        return obj.participants.count()

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data) 