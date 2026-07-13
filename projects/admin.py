from django.contrib import admin
from projects.models import Project, ProjectAssignment, ProjectSubmission

admin.site.register(Project)
admin.site.register(ProjectAssignment)
admin.site.register(ProjectSubmission)