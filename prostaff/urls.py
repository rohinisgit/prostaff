from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('employees/', include('employees.urls')),
    path('attendance/', include('attendance.urls')),
    path('payroll/', include('payroll.urls')),
    path('increments/', include('increments.urls')),
    path('projects/', include('projects.urls')),
    path('leaves/', include('leaves.urls')),
    path('queries/', include('queries.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
