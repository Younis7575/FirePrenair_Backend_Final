from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Like)
admin.site.register(ReplyComment)
admin.site.register(Group)
admin.site.register(Event)
admin.site.register(GroupMemberShipRequests)
admin.site.register(FriendRequest)
admin.site.register(Connection)
admin.site.register(Message)
admin.site.register(PrivateChat)
admin.site.register(Groupcategory)
