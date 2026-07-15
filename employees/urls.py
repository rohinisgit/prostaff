from django.urls import path
from employees import views

app_name = 'employees'

urlpatterns = [
    path('me/', views.my_profile, name='my_profile'),
    path('me/upload-document/', views.upload_own_document, name='upload_own_document'),
    path('resignation/apply/', views.apply_resignation, name='apply_resignation'),
path('resignation/', views.resignation_list, name='resignation_list'),
path('resignation/<int:resignation_id>/approve/', views.approve_resignation, name='approve_resignation'),
path('resignation/<int:resignation_id>/reject/', views.reject_resignation, name='reject_resignation'),
path('resignation/<int:resignation_id>/negotiate/', views.negotiate_resignation, name='negotiate_resignation'),
path('resignation/<int:resignation_id>/accept-offer/', views.accept_resignation_offer, name='accept_resignation_offer'),
path('resignation/<int:resignation_id>/quit-anyway/', views.quit_after_negotiation, name='quit_after_negotiation'),
    path('directory/', views.employee_directory, name='directory'),
    path('onboard/', views.onboard_employee, name='onboard'),
    path('onboarding/', views.onboarding_list, name='onboarding_list'),
    path('<int:user_id>/', views.employee_detail, name='employee_detail'),
    path('<int:user_id>/edit-profile/', views.edit_employee_profile, name='edit_employee_profile'),
    path('<int:user_id>/upload-document/', views.upload_document, name='upload_document'),
    path('<int:user_id>/delete/', views.delete_employee, name='delete_employee'),
    path('<int:user_id>/change-role/', views.change_role, name='change_role'),
    path('my-department/', views.my_department, name='my_department'),
    path('<int:user_id>/team-member/', views.team_member_detail, name='team_member_detail'),
    path('<int:user_id>/complete-onboarding/', views.complete_onboarding, name='complete_onboarding'),

]