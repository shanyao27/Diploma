from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import Admin, Inspector, User, Department, Position
from .models import Medic

class MedicAdmin(admin.ModelAdmin):
    list_display = ('login', 'full_name', 'department', 'isActive')
    list_filter = ('isActive', 'department')
    search_fields = ('login', 'full_name')
    
    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'department')}),
        ('Права доступа', {'fields': ('isActive',)}),
    )
    
    def save_model(self, request, obj, form, change):
        if 'password' in form.changed_data and obj.password:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)


class AdminAdmin(admin.ModelAdmin):
    """Настройка отображения Admin в админке"""
    list_display = ('login', 'full_name', 'department', 'is_global_admin', 'isActive')
    list_filter = ('is_global_admin', 'isActive', 'department')
    search_fields = ('login', 'full_name')
    
    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'department')}),
        ('Права доступа', {'fields': ('is_global_admin', 'isActive')}),
    )
    
    def save_model(self, request, obj, form, change):
        """Хешируем пароль при сохранении"""
        if 'password' in form.changed_data:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


# ==========================================
# 2. НАСТРОЙКА ДЛЯ МОДЕЛИ INSPECTOR
# ==========================================

class InspectorAdmin(admin.ModelAdmin):
    """Настройка отображения Inspector в админке"""
    list_display = ('login', 'full_name', 'department', 'isActive')
    list_filter = ('isActive', 'department')
    search_fields = ('login', 'full_name')
    
    fieldsets = (
        (None, {'fields': ('login', 'password')}),
        ('Персональная информация', {'fields': ('full_name', 'department')}),
        ('Права доступа', {'fields': ('isActive',)}),
    )
    
    def save_model(self, request, obj, form, change):
        """Хешируем пароль при сохранении"""
        if 'password' in form.changed_data:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


class UserAdmin(admin.ModelAdmin):
    """Настройка отображения User в админке"""
    list_display = ('FIO', 'login', 'department', 'system_role', 'isActive', 'employment_status')
    list_filter = ('isActive', 'system_role', 'employment_status', 'department')
    search_fields = ('FIO', 'login', 'number', 'passportData')
    readonly_fields = ('password',)  # Пароль только для чтения
    fieldsets = (
        ('Основная информация', {'fields': ('FIO', 'login', 'password', 'passportData', 'number', 'address')}),
        ('Работа', {'fields': ('department', 'position', 'role', 'manager', 'system_role')}),
        ('Статус', {'fields': ('isActive', 'employment_status', 'hire_date')}),
        ('Аттестации', {'fields': ('certifications', 'assigned_certifications')}),
        ('Документы', {'fields': ('documents',)}),
    )

admin.site.register(Admin, AdminAdmin)
admin.site.register(Inspector, InspectorAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Department)
admin.site.register(Position)
admin.site.register(Medic, MedicAdmin)