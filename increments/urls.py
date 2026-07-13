from django.urls import path
from increments import views

app_name = 'increments'

urlpatterns = [
    path('', views.increment_list, name='list'),
    path('create/', views.create_increment, name='create'),
    path('<int:increment_id>/approve/', views.approve_increment, name='approve'),
    path('<int:increment_id>/reject/', views.reject_increment, name='reject'),
    path('feedback/', views.manager_feedback_list, name='manager_feedback_list'),
    path('<int:increment_id>/feedback/', views.submit_increment_feedback, name='submit_feedback'),
    path('due/<int:user_id>/dismiss/', views.dismiss_due_increment, name='dismiss_due_increment'),
    path('history/<int:user_id>/', views.increment_history_detail, name='history_detail'),
]