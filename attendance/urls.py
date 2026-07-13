from django.urls import path
from attendance import views

app_name = 'attendance'

urlpatterns = [
    path('punch/', views.punch, name='punch'),
    path('me/', views.my_attendance, name='my_attendance'),
    path('reports/', views.attendance_reports, name='reports'),
    path('reports/<int:user_id>/', views.employee_attendance, name='employee_attendance'),
]