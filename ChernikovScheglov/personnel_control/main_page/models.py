from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import RegexValidator
from django.utils import timezone


class PublishedModel(models.Model):
    """Абстрактная модель для ролей"""

    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    password = models.CharField(max_length=128, verbose_name="Пароль")
    isActive = models.BooleanField(default=False, verbose_name="Активен")
    isAdmin = models.BooleanField(verbose_name="Администратор")
    isInspector = models.BooleanField(verbose_name="Инспектор")

    class Meta:
        abstract = True
    
    # ДОБАВЬТЕ ЭТИ МЕТОДЫ:
    def set_password(self, raw_password):
        """Хеширует пароль перед сохранением"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Проверяет пароль с хешем в БД"""
        return check_password(raw_password, self.password)
    
    def save(self, *args, **kwargs):
        # Хешируем пароль, если он еще не захеширован
        if self.password and not self.password.startswith(('pbkdf2_', 'bcrypt_', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


class Department(models.Model):
    """Подразделение / участок предприятия."""

    name = models.CharField(max_length=150, unique=True, verbose_name="Название участка")
    code = models.CharField(max_length=30, unique=True, verbose_name="Код участка")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "участок"
        verbose_name_plural = "Участки"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(models.Model):
    """Должность сотрудника, привязанная к участку."""

    name = models.CharField(max_length=150, verbose_name="Должность")
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Участок",
    )
    is_managerial = models.BooleanField(default=False, verbose_name="Руководящая")
    requires_medical_check = models.BooleanField(default=True, verbose_name="Требует медосмотра")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "должность"
        verbose_name_plural = "Должности"
        ordering = ["department__name", "name"]
        unique_together = ["department", "name"]

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class Admin(PublishedModel):
    """Модель администратора"""

    isAdmin = models.BooleanField(default=True, verbose_name="Администратор")
    isInspector = models.BooleanField(default=False, verbose_name="Инспектор")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="department_admins",
        verbose_name="Закрепленный участок",
    )
    is_global_admin = models.BooleanField(default=False, verbose_name="Глобальный администратор")
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")

    class Meta:
        verbose_name = "администратор"
        verbose_name_plural = "Администраторы"

    def __str__(self):
        return self.full_name or self.login


class Inspector(PublishedModel):
    """Модель инспектора"""

    isAdmin = models.BooleanField(default=False, verbose_name="Администратор")
    isInspector = models.BooleanField(default=True, verbose_name="Инспектор")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspectors",
        verbose_name="Закрепленный участок",
    )
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")

    class Meta:
        verbose_name = "инспектор"
        verbose_name_plural = "Инспекторы"

    def __str__(self):
        return self.full_name or self.login
    
    
class Medic(PublishedModel):
    """Модель медработника (аналогична Inspector)"""
    
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medics',
        verbose_name='Закрепленный участок',
    )
    
    class Meta:
        verbose_name = "медработник"
        verbose_name_plural = "Медработники"
    
    def __str__(self):
        return self.full_name or self.login
    

class User(models.Model):
    """Модель сотрудника"""

    phone_regex = RegexValidator(
        regex=r'^\+?7?\d{10,15}$',
        message="Номер телефона должен быть в формате: '+79991234567'"
    )

    passport_regex = RegexValidator(
        regex=r'^\d{4}\s?\d{6}$',
        message="Паспорт должен быть в формате: 1234 567890"
    )

    ROLE_CHOICES = [
        ('worker', 'Сотрудник'),
        ('lead', 'Старший сотрудник'),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('active', 'Работает'),
        ('suspended', 'Отстранен'),
        ('sick_leave', 'На больничном'),
        ('dismissed', 'Уволен'),
    ]

    SYSTEM_ROLE_CHOICES = [
        ('employee', 'Сотрудник'),
        ('manager', 'Начальник участка'),
        # ('medic', 'Медработник'),
        # ('inspector', 'Инспектор'),
        # ('global_admin', 'Глобальный администратор'),
    ]

    passportData = models.CharField(
        max_length=11,
        validators=[passport_regex],
        verbose_name="Серия и номер паспорта"
    )
    FIO = models.CharField(max_length=255, verbose_name="ФИО")
    number = models.CharField(max_length=15, validators=[phone_regex], verbose_name="Номер телефона")
    address = models.CharField(max_length=255, verbose_name="Адрес")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, verbose_name="Роль")
    login = models.CharField(max_length=50, unique=True, verbose_name="Логин")
    password = models.CharField(max_length=128, verbose_name="Пароль")
    isActive = models.BooleanField(default=False, verbose_name="Уволен или работает")
    isAdmin = models.BooleanField(default=False, verbose_name="Администратор")
    isInspector = models.BooleanField(default=False, verbose_name="Инспектор")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Участок',
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        verbose_name='Должность',
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members',
        verbose_name='Непосредственный начальник',
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='Статус трудоустройства',
    )
    system_role = models.CharField(
        max_length=20,
        choices=SYSTEM_ROLE_CHOICES,
        default='employee',
        verbose_name='Системная роль',
    )
    hire_date = models.DateField(null=True, blank=True, verbose_name='Дата приема на работу')
    certifications = models.JSONField(default=list, blank=True, verbose_name="Список аттестаций")
    assigned_certifications = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Назначенные аттестации",
        help_text="ID тестов, которые нужно пройти"
    )
    documents = models.JSONField(default=list, blank=True, verbose_name="Список документов")

    @property
    def noDocuments(self):
        from profiles.models import DocumentSignature
        assigned = self.documents
        if not assigned:
            return True
        signed = DocumentSignature.objects.filter(user=self, document_id__in=assigned).count()
        return len(assigned) == signed

    @property
    def noCertifications(self):
        return len(self.assigned_certifications) == 0

    @property
    def has_pending_certifications(self):
        return len(self.assigned_certifications) > 0

    @property
    def active_sick_leave(self):
        today = timezone.localdate()
        return self.sick_leaves.filter(start_date__lte=today, end_date__gte=today, status='active').order_by('-start_date').first()

    @property
    def todays_medical_check(self):
        today = timezone.localdate()
        return self.medical_checks.filter(
            check_date=today,
            check_type='morning'
        ).order_by('-check_date', '-checked_at').first()

    @property
    def can_start_work_today(self):
        check = self.todays_medical_check
        return bool(check and check.decision == 'fit')

    @property
    def AllowedToWork(self):
        return (
            self.isActive
            and self.employment_status == 'active'
            and self.noCertifications
            and self.noDocuments
            and self.active_sick_leave is None
            and self.can_start_work_today
            and self.active_block is None
        )


    @property
    def active_block(self):
        from django.utils import timezone as dj_timezone
        from profiles.models import UserBlock
        return UserBlock.objects.filter(user=self, expires_at__gt=dj_timezone.now()).order_by('-expires_at').first()

    @property
    def sanction_counts(self):
        from profiles.models import Sanction
        counts = {'warning': 0, 'explanation': 0, 'fine': 0, 'suspension': 0, 'dismissal_notice': 0, 'other': 0}
        for item in Sanction.objects.filter(employee=self).exclude(status='cancelled'):
            key = item.sanction_type if item.sanction_type in counts else 'other'
            counts[key] += 1
        return counts

    @property
    def needs_attention(self):
        counts = self.sanction_counts
        return counts['warning'] >= 5 or counts['fine'] >= 3 or sum(counts.values()) >= 7

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    def save(self, *args, **kwargs):
        if not self.pk or not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        if self.isActive and self.employment_status == 'pending':
            self.employment_status = 'active'
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    class Meta:
        verbose_name = "сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return f"{self.FIO} ({self.login})"
