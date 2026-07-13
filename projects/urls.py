from django.urls import path
from projects import views

app_name = 'projects'

urlpatterns = [
    path('', views.project_list, name='list'),
    path('create/', views.create_project, name='create'),
    path('approvals/', views.project_approvals, name='approvals'),
    path('<int:project_id>/approve/', views.approve_project, name='approve'),
    path('<int:project_id>/reject/', views.reject_project, name='reject'),
    path('me/history/', views.my_project_history, name='my_history'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    path('<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('<int:project_id>/complete/', views.complete_project, name='complete_project'),
    path('<int:project_id>/submit-update/', views.submit_project_update, name='submit_update'),
    path('submission/<int:submission_id>/<str:decision>/', views.review_project_submission, name='review_submission'),
]