from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(PayoutAccount)
admin.site.register(WithdrawalRequest)
admin.site.register(TrafficLog)
admin.site.register(Template)
admin.site.register(TemplateCategory)
admin.site.register(UserWebsite)
admin.site.register(Funnel)
admin.site.register(FunnelStep)
admin.site.register(FunnelProduct)
admin.site.register(FunnelOrder)
admin.site.register(FunnelLead)
admin.site.register(KYCProfile)