import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Room, Message
from .serializers import MessageSerializer
import time

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Get token from query parameters
        query_string = self.scope['query_string'].decode()
        token = dict(x.split('=') for x in query_string.split('&')).get('token', None)

        if not token:
            await self.close()
            return

        # Authenticate user
        try:
            self.user = await self.get_user_from_token(token)
            if not self.user:
                await self.close()
                return

            # Check if user is a participant of the room
            is_participant = await self.is_room_participant(self.room_id, self.user)
            if not is_participant:
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

            # Send message history
            messages = await self.get_message_history(self.room_id)
            if messages:
                await self.send(text_data=json.dumps({
                    'type': 'message_history',
                    'messages': messages
                }))

        except Exception as e:
            print(f"Connection error: {str(e)}")
            await self.close()
            return

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json['message'].strip()
            
            if not message_content:  # Boş mesajları engelle
                return

            # Save message to database
            saved_message = await self.save_message(self.room_id, self.user.id, message_content)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'sender': self.user.username,
                    'timestamp': int(time.mktime(saved_message['timestamp'].timetuple()) * 1000),
                    'message_id': saved_message['id']
                }
            )
        except json.JSONDecodeError:
            print("Invalid JSON received")
        except KeyError:
            print("Missing 'message' in received data")
        except Exception as e:
            print(f"Error processing message: {str(e)}")

    async def chat_message(self, event):
        try:
            # Send message to WebSocket
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': event['message'],
                'sender': event['sender'],
                'timestamp': event['timestamp'],
                'message_id': event['message_id']
            }))
        except Exception as e:
            print(f"Error sending message: {str(e)}")

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def is_room_participant(self, room_id, user):
        try:
            room = Room.objects.get(id=room_id)
            return room.participants.filter(id=user.id).exists() or room.owner == user
        except Room.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, room_id, user_id, content):
        room = Room.objects.get(id=room_id)
        user = User.objects.get(id=user_id)
        message = Message.objects.create(
            room=room,
            sender=user,
            content=content
        )
        return MessageSerializer(message).data

    @database_sync_to_async
    def get_message_history(self, room_id):
        room = Room.objects.get(id=room_id)
        messages = room.messages.all()
        return MessageSerializer(messages, many=True).data