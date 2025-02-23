import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("chat", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("chat", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                data = json.loads(text_data)
                message_type = data.get('type', 'message')
                username = data.get('username', '')

                if message_type == 'typing':
                    # Handle typing status
                    await self.channel_layer.group_send(
                        "chat",
                        {
                            'type': 'typing_status',
                            'username': username,
                            'is_typing': data.get('is_typing', False)
                        }
                    )
                else:
                    # Handle regular message
                    await self.channel_layer.group_send(
                        "chat",
                        {
                            'type': 'chat_message',
                            'message': data.get('message', ''),
                            'username': username,
                        }
                    )
        except json.JSONDecodeError as e:
            print(f"Invalid JSON received: {e}")
        except Exception as e:
            print(f"Error processing message: {str(e)}")

    async def chat_message(self, event):
        try:
            message_data = {
                'type': 'message',
                'message': event['message'],
                'username': event['username']
            }
            await self.send(text_data=json.dumps(message_data))
        except Exception as e:
            print(f"Error sending chat message: {str(e)}")

    async def typing_status(self, event):
        try:
            typing_data = {
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing']
            }
            await self.send(text_data=json.dumps(typing_data))
        except Exception as e:
            print(f"Error sending typing status: {str(e)}") 