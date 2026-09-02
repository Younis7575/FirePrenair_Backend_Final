import json
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from asgiref.sync import sync_to_async
from .models import CustomUser

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            await self.set_user_online_status(online=True)

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            await self.set_user_online_status(online=False)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event['content']))

    @sync_to_async
    def set_user_online_status(self, online):
        user = CustomUser.objects.get(id=self.user.id)
        user.is_online = online
        if not online:
            user.last_seen = now()
        user.save()
