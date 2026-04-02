from django.contrib import admin
from .models import Admin, Inspector, User, Department, Position

admin.site.register(Admin)
admin.site.register(Inspector)
admin.site.register(User)
admin.site.register(Department)
admin.site.register(Position)