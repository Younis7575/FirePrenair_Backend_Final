from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import handler404, handler500
from django.conf.urls.i18n import set_language
from django.urls import path



urlpatterns = [
    path("admin/", admin.site.urls),
    
    path("accounts/", include("allauth.urls")),
    
    path("", include("home.urls")),
    path("digiprenair/", include("digi_prenair.urls")),
    path("eduprenair/", include("edu_prenair.urls")),
    path("commuprenair/", include("commu_prenair.urls")),
    path("workprenair/", include("work_prenair.urls")),
    path("my_accounts/", include("profiles.urls")),
    path("dashboard/", include("dashboard.urls")),
    path('i18n/setlang/', set_language, name='set_language'),

    #### Rest Api's URL
    path("api/", include("core_api.urls")),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler404 = 'home.views.custom_404'
handler500 = 'home.views.custom_500'