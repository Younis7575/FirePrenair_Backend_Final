import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Message, PrivateChat
from channels.db import database_sync_to_async
from profiles.models import CustomUser as User
import base64
from django.core.files.base import ContentFile

class ChatConsumer(AsyncWebsocketConsumer):
    room_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        self.chat_slug = self.scope['url_route']['kwargs']['slug']

        # An anonymous socket used to be accepted and then blow up in
        # set_user_online, which calls save() on AnonymousUser.
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        try:
            self.chat = await database_sync_to_async(PrivateChat.objects.get)(
                slug=self.chat_slug
            )
        except PrivateChat.DoesNotExist:
            # A bad slug raised inside connect(), which surfaces as the
            # same silent drop rather than a refusal the client can read.
            await self.close(code=4404)
            return

        self.room_group_name = f'chat_{self.chat_slug}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.set_user_online(self.user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user': self.user.username,
                'status': 'online'
            }
        )

        await self.accept()

    async def disconnect(self, close_code):
        # connect() may have refused before the group was joined.
        if not self.room_group_name:
            return
        await self.set_user_offline(self.user)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user': self.user.username,
                'status': 'offline'
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def set_user_online(self, user):
        user.is_online = True
        user.save()

    @database_sync_to_async
    def set_user_offline(self, user):
        user.is_online = False
        user.save()

    async def receive(self, text_data):
        data = json.loads(text_data)
        sender = self.user
        receiver = await self.get_receiver(sender)

        if 'message' in data:  # Handling text message
            message = data['message']
            msg = await database_sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=sender,
                receiver=receiver,
                content=message
            )
            await self.send_message_to_group(message=msg.content, sender=sender.username)

        elif 'file_name' in data and 'file_data' in data:  # Handling file upload
            file_name = data['file_name']
            file_data = data['file_data'].split(';base64,')[1]
            decoded_file = ContentFile(base64.b64decode(file_data), name=file_name)
            
            msg = await database_sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=sender,
                receiver=receiver,
                file=decoded_file
            )
            await self.send_file_to_group(file_name=msg.file.url, sender=sender.username)

    async def send_message_to_group(self, message, sender):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender
            }
        )

    async def send_file_to_group(self, file_name, sender):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'file_message',
                'file_name': file_name,
                'sender': sender
            }
        )

    async def file_message(self, event):
        # This method handles the `file_message` event to send it to WebSocket
        file_name = event['file_name']
        sender = event['sender']

        await self.send(text_data=json.dumps({
            'type': 'file_message',
            'file_name': file_name,
            'sender': sender
        }))

    @database_sync_to_async
    def get_receiver(self, sender):
        return self.chat.user1 if sender != self.chat.user1 else self.chat.user2
    
    async def user_status(self, event):
        user = event['user']
        status = event['status']
        
        await self.send(text_data=json.dumps({
            'user': user,
            'status': status
        }))

    async def chat_message(self, event):
        message = event['message']
        sender = event['sender']

        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender
        }))
