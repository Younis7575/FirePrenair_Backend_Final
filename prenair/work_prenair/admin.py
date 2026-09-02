from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Category)
admin.site.register(Gig)
admin.site.register(Tag)
admin.site.register(Order)
admin.site.register(Delivery)
admin.site.register(RevisionRequest)
admin.site.register(Review)
admin.site.register(CustomOffer)
admin.site.register(Badge)
admin.site.register(Todo)