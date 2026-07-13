from django.urls import path
from leaves import views

app_name = 'leaves'

urlpatterns = [
    path('me/', views.my_leaves, name='my_leaves'),
    path('approvals/', views.leave_approvals, name='approvals'),
    path('<int:leave_id>/<str:decision>/', views.review_leave, name='review_leave'),
]
