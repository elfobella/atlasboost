from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Todo(models.Model):
    title = models.CharField(max_length=200)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Room(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_rooms')
    participants = models.ManyToManyField(User, related_name='joined_rooms')

    def __str__(self):
        return self.name

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    BOOSTER = 'BOOSTER', 'Booster'
    CUSTOMER = 'CUSTOMER', 'Customer'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

class Message(models.Model):
    room = models.ForeignKey('Room', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
