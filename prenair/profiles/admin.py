from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(CustomUser)
admin.site.register(Notification)  


admin.site.site_header = "FirePrenair Administration"
admin.site.site_title = "FirePrenair Admin Portal"
admin.site.index_title = "Welcome to FirePrenair Admin Portal"