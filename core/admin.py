from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.utils.safestring import mark_safe
from core.models import User, Department

admin.site.register(Department)


class SimpleUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password' in self.fields:
            del self.fields['password']


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = SimpleUserChangeForm

    fieldsets = (
        (None, {'fields': ('username', 'reset_password_link')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('HRMS Info', {'fields': ('role', 'employee_id', 'department', 'manager', 'date_joined_company', 'phone')}),
        ('Access', {'fields': ('is_active',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'employee_id'),
        }),
    )

    list_display = ('username', 'first_name', 'last_name', 'role', 'department', 'is_active')
    list_filter = ('role', 'department', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'employee_id')

    def get_readonly_fields(self, request, obj=None):
        # Admin accounts are top priority — their role can never be changed,
        # from here or anywhere else in the app.
        if obj and obj.role == 'ADMIN':
            return ('reset_password_link', 'role')
        return ('reset_password_link',)

    def reset_password_link(self, obj):
        if obj and obj.pk:
            return mark_safe('<a href="../password/">Reset this user\'s password</a>')
        return "-"

    reset_password_link.short_description = "Password"