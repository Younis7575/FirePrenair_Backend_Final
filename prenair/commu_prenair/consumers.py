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

        # Only the two participants may join a conversation; knowing the slug
        # was enough to read and post in anyone's chat.
        if self.user.id not in (self.chat.user1_id, self.chat.user2_id):
            await self.close(code=4403)
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
        from django.utils.timezone import now
        user.is_online = False
        # The website's chat header shows "Last seen: <time_since_last_seen>".
        user.last_seen = now()
        user.save()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return
        if not isinstance(data, dict):
            return
        sender = self.user

        # Typing indicator: {"type": "typing", "typing": true|false}
        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'user': sender.username,
                    'typing': bool(data.get('typing', True)),
                },
            )
            return

        # Read receipts: {"type": "read"} marks everything the other
        # participant sent as read and tells the room which ids changed.
        if data.get('type') == 'read':
            ids = await self.mark_read(sender)
            if ids:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'read_receipt',
                        'user': sender.username,
                        'message_ids': ids,
                    },
                )
            return

        receiver = await self.get_receiver(sender)

        if 'message' in data:  # Handling text message
            message = data['message']
            msg = await database_sync_to_async(Message.objects.create)(
                chat=self.chat,
                sender=sender,
                receiver=receiver,
                content=message
            )
            await self.send_message_to_group(
                message=msg.content, sender=sender.username, message_id=msg.id,
                timestamp=msg.timestamp.isoformat(),
            )

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
            await self.send_file_to_group(
                file_name=msg.file.url, sender=sender.username, message_id=msg.id,
                timestamp=msg.timestamp.isoformat(),
            )

    async def send_message_to_group(self, message, sender, message_id=None, timestamp=None):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': sender,
                'id': message_id,
                'timestamp': timestamp,
            }
        )

    async def send_file_to_group(self, file_name, sender, message_id=None, timestamp=None):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'file_message',
                'file_name': file_name,
                'sender': sender,
                'id': message_id,
                'timestamp': timestamp,
            }
        )

    async def file_message(self, event):
        # This method handles the `file_message` event to send it to WebSocket
        file_name = event['file_name']
        sender = event['sender']

        await self.send(text_data=json.dumps({
            'type': 'file_message',
            'file_name': file_name,
            'sender': sender,
            'id': event.get('id'),
            'timestamp': event.get('timestamp'),
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
            'sender': sender,
            'id': event.get('id'),
            'timestamp': event.get('timestamp'),
        }))

    @database_sync_to_async
    def mark_read(self, user):
        qs = Message.objects.filter(chat=self.chat, receiver=user, is_read=False)
        ids = list(qs.values_list('id', flat=True))
        if ids:
            Message.objects.filter(id__in=ids).update(is_read=True)
        return ids

    async def typing_status(self, event):
        # The sender already knows it is typing.
        if event['user'] == self.user.username:
            return
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user': event['user'],
            'typing': event['typing'],
        }))

    async def read_receipt(self, event):
        if event['user'] == self.user.username:
            return
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user': event['user'],
            'message_ids': event['message_ids'],
        }))
