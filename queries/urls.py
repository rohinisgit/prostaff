from django.urls import path
from queries import views

app_name = 'queries'

urlpatterns = [
    path('me/', views.my_queries, name='my_queries'),
    path('<int:query_id>/', views.query_thread, name='query_thread'),
    path('<int:query_id>/delete/', views.delete_query, name='delete_query'),
    path('hr/', views.hr_queries, name='hr_queries'),
    path('admin/', views.admin_queries, name='admin_queries'),
    path('manager/', views.manager_queries, name='manager_queries'),
]