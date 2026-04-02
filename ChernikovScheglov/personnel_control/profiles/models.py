from django.db import models
from main_page.models import User, Admin, Inspector, Department
from django.utils import timezone
from datetime import timedelta, time


class Camera(models.Model):
    """Камера видеонаблюдения, закрепленная за участком."""

    name = models.CharField(max_length=150, verbose_name='Название камеры')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='cameras',
        verbose_name='Участок',
    )
    zone = models.CharField(max_length=150, blank=True, verbose_name='Зона / локация')
    description = models.TextField(blank=True, verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'камера'
        verbose_name_plural = 'Камеры'
        ordering = ['department__name', 'name']

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class ViolationType(models.Model):
    CATEGORY_CHOICES = [
        ('medical', 'Медосмотр'),
        ('work_order', 'Наряд'),
        ('ppe', 'СИЗ'),
        ('discipline', 'Дисциплина'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Легкое'),
        ('medium', 'Среднее'),
        ('high', 'Тяжелое'),
        ('critical', 'Критическое'),
    ]

    SANCTION_CHOICES = [
        ('warning', 'Предупреждение'),
        ('explanation', 'Объяснительная'),
        ('fine', 'Штраф / лишение премии'),
        ('suspension', 'Отстранение'),
        ('dismissal_notice', 'Уведомление на увольнение'),
    ]

    name = models.CharField(max_length=150, unique=True, verbose_name='Тип нарушения')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='Категория')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name='Тяжесть')
    default_sanction = models.CharField(max_length=30, choices=SANCTION_CHOICES, default='warning', verbose_name='Базовая санкция')
    default_comment = models.TextField(blank=True, verbose_name='Комментарий')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    class Meta:
        verbose_name = 'тип нарушения'
        verbose_name_plural = 'Типы нарушений'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class WorkObject(models.Model):
    """Модель заказ-наряда / наряд-задания."""

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('recruiting', 'Набор сотрудников'),
        ('waiting', 'Ожидание начала'),
        ('in_progress', 'В работе'),
        ('paused', 'На паузе'),
        ('extended', 'Продлен'),
        ('completed', 'Завершен'),
        ('overdue', 'Просрочен'),
        ('cancelled', 'Отменен'),
    ]

    address = models.CharField(max_length=200, blank=True, default='', verbose_name="Адрес")
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_objects',
        verbose_name='Участок',
    )
    zone = models.CharField(max_length=150, blank=True, verbose_name='Зона выполнения работ')
    work_type = models.CharField(max_length=150, blank=True, verbose_name='Вид работ')
    description = models.TextField(blank=True, verbose_name='Описание задания')
    employeesNeeded = models.IntegerField(default=1, verbose_name="Требуется сотрудников")
    employeesReady = models.BooleanField(default=False, verbose_name="Укомплектован")
    employees = models.ManyToManyField('main_page.User', blank=True, related_name='works', verbose_name="Записанные сотрудники")
    leadEmployee = models.ForeignKey('main_page.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='lead_works', verbose_name="Старший сотрудник")
    responsible_admin = models.ForeignKey(
        Admin,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_work_objects',
        verbose_name='Ответственный руководитель',
    )
    payment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Оплата")
    time = models.DateTimeField(verbose_name="Дата и время проведения")
    duration = models.IntegerField(default=2, verbose_name="Продолжительность (часы)")
    close_grace_minutes = models.PositiveIntegerField(default=60, verbose_name='Допустимая просрочка закрытия (мин)')
    planned_end_time = models.DateTimeField(null=True, blank=True, verbose_name='Плановое окончание')
    actual_start_time = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое начало')
    actual_end_time = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое окончание')
    extended_until = models.DateTimeField(null=True, blank=True, verbose_name='Продлено до')
    extension_reason = models.TextField(blank=True, verbose_name='Причина продления')
    completion_comment = models.TextField(blank=True, verbose_name='Комментарий по закрытию')
    last_signup_time = models.DateTimeField(null=True, blank=True, verbose_name="Последняя запись")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")

    class Meta:
        verbose_name = "Заказ-наряд"
        verbose_name_plural = "Заказ-наряды"
        ordering = ['-time']

    def __str__(self):
        return f"Наряд #{self.id} - {self.zone or self.address or self.work_type or 'без названия'}"

    @property
    def assigned_employees_count(self):
        return self.employees.count()

    @property
    def can_assign_lead(self):
        return self.status not in ['completed', 'cancelled'] and self.employees.exists()

    @property
    def is_waiting(self):
        return self.status == 'waiting'

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def deadline(self):
        return self.extended_until or self.planned_end_time or self.time

    def update_status(self):
        now = timezone.now()

        if self.status in ['cancelled', 'completed']:
            return self.status

        if self.actual_start_time and not self.actual_end_time:
            self.status = 'in_progress'

        if self.deadline and now > self.deadline and self.status not in ['completed', 'cancelled']:
            self.status = 'overdue'

        elif self.employees.count() >= self.employeesNeeded and self.status in ['draft', 'recruiting']:
            self.status = 'waiting'
            self.employeesReady = True

        elif self.status == 'draft':
            self.status = 'recruiting'

        self.save(update_fields=['status', 'employeesReady'])
        return self.status

    def save(self, *args, **kwargs):
        if self.time and not self.planned_end_time:
            self.planned_end_time = self.time + timedelta(hours=self.duration or 0)
        if self.status == 'draft' and self.pk:
            if self.employees.count() >= self.employeesNeeded:
                self.status = 'waiting'
            else:
                self.status = 'recruiting'
        super().save(*args, **kwargs)


class MedicalCheck(models.Model):
    CHECK_TYPE_CHOICES = [
        ('morning', 'Утренний осмотр'),
        ('evening', 'Вечерний осмотр'),
    ]

    DECISION_CHOICES = [
        ('fit', 'Допущен'),
        ('unfit', 'Не допущен'),
    ]

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='medical_checks',
        verbose_name='Сотрудник',
    )
    medic = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_medical_checks',
        verbose_name='Медработник',
    )
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES, verbose_name='Тип осмотра')
    check_date = models.DateField(default=timezone.localdate, verbose_name='Дата осмотра')
    checked_at = models.DateTimeField(default=timezone.now, verbose_name='Время отметки')
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, verbose_name='Решение')
    blood_pressure = models.CharField(max_length=20, blank=True, verbose_name='Давление')
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='Температура')
    pulse = models.PositiveIntegerField(null=True, blank=True, verbose_name='Пульс')
    complaints = models.TextField(blank=True, verbose_name='Жалобы')
    alcohol_free = models.BooleanField(default=True, verbose_name='Трезв')
    sanction_reason = models.CharField(max_length=255, blank=True, verbose_name='Основание')
    sanction_type = models.CharField(max_length=30, choices=ViolationType.SANCTION_CHOICES, blank=True, verbose_name='Санкция')
    comment = models.TextField(blank=True, verbose_name='Комментарий медика')

    class Meta:
        verbose_name = 'медицинский осмотр'
        verbose_name_plural = 'Медицинские осмотры'
        ordering = ['-checked_at']
        unique_together = ['employee', 'check_type', 'check_date']

    def __str__(self):
        return f"{self.employee.FIO} - {self.get_check_type_display()} - {self.check_date}"

    @property
    def is_within_required_window(self):
        local_time = timezone.localtime(self.checked_at).time()
        if self.check_type == 'morning':
            return time(5, 0) <= local_time <= time(7, 0)
        return True


class SickLeave(models.Model):
    STATUS_CHOICES = [
        ('active', 'Активен'),
        ('closed', 'Закрыт'),
        ('cancelled', 'Отменен'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sick_leaves', verbose_name='Сотрудник')
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_sick_leaves', verbose_name='Выдал')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    reason = models.CharField(max_length=255, verbose_name='Причина')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'больничный'
        verbose_name_plural = 'Больничные'
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee.FIO}: {self.start_date} - {self.end_date}"


class Sanction(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Действует'),
        ('cancelled', 'Отменена'),
        ('expired', 'Истекла'),
    ]

    SANCTION_CHOICES = [
        ('warning', 'Предупреждение'),
        ('explanation', 'Объяснительная'),
        ('fine', 'Лишение премии / штраф'),
        ('suspension', 'Отстранение'),
        ('dismissal_notice', 'Уведомление на увольнение'),
    ]

    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sanctions', verbose_name='Сотрудник')
    violation_type = models.ForeignKey(ViolationType, on_delete=models.SET_NULL, null=True, blank=True, related_name='sanctions', verbose_name='Основание')
    work_object = models.ForeignKey(WorkObject, on_delete=models.SET_NULL, null=True, blank=True, related_name='sanctions', verbose_name='Наряд')
    created_by_admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sanctions', verbose_name='Назначил администратор')
    sanction_type = models.CharField(max_length=30, choices=SANCTION_CHOICES, verbose_name='Вид санкции')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Размер удержания')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    starts_at = models.DateField(default=timezone.localdate, verbose_name='Дата начала')
    expires_at = models.DateField(null=True, blank=True, verbose_name='Истекает')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создана')

    class Meta:
        verbose_name = 'санкция'
        verbose_name_plural = 'Санкции'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.FIO} - {self.get_sanction_type_display()}"


class CertificationTest(models.Model):
    title = models.CharField('Название', max_length=200)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='certification_tests', verbose_name='Участок')
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    created_by_admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tests', verbose_name='Создал (админ)')
    created_by_inspector = models.ForeignKey(Inspector, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tests', verbose_name='Создал (инспектор)')

    @property
    def created_by(self):
        return self.created_by_admin or self.created_by_inspector

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'тест аттестации'
        verbose_name_plural = 'Тесты аттестации'


class Question(models.Model):
    test = models.ForeignKey(CertificationTest, on_delete=models.CASCADE, related_name='questions', verbose_name='Тест')
    text = models.TextField('Текст вопроса', help_text='Введите текст вопроса')
    option1 = models.CharField('Вариант 1', max_length=200, help_text='Первый вариант ответа')
    option2 = models.CharField('Вариант 2', max_length=200, help_text='Второй вариант ответа')
    option3 = models.CharField('Вариант 3', max_length=200, help_text='Третий вариант ответа')
    correct_answer = models.IntegerField('Правильный ответ', choices=[(1, 'Вариант 1'), (2, 'Вариант 2'), (3, 'Вариант 3')], help_text='Выберите номер правильного ответа')

    def __str__(self):
        return self.text[:50]

    class Meta:
        verbose_name = 'вопрос'
        verbose_name_plural = 'Вопросы'


class UserTestAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts', verbose_name='Сотрудник')
    test = models.ForeignKey(CertificationTest, on_delete=models.CASCADE, related_name='attempts', verbose_name='Тест')
    started_at = models.DateTimeField('Начало', auto_now_add=True)
    completed_at = models.DateTimeField('Завершение', null=True, blank=True)
    passed = models.BooleanField('Сдал?', default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.passed and self.completed_at:
            if self.test.id not in self.user.certifications:
                self.user.certifications.append(self.test.id)
                if self.test.id in self.user.assigned_certifications:
                    self.user.assigned_certifications.remove(self.test.id)
                self.user.save(update_fields=['certifications', 'assigned_certifications'])

    @property
    def is_completed(self):
        return self.completed_at is not None

    def __str__(self):
        status = '✅' if self.passed else '❌' if self.completed_at else '⏳'
        return f"{self.user.FIO} - {self.test.title} {status}"

    class Meta:
        verbose_name = 'попытка'
        verbose_name_plural = 'Попытки'


class UserAnswer(models.Model):
    attempt = models.ForeignKey(UserTestAttempt, on_delete=models.CASCADE, related_name='answers', verbose_name='Попытка')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='Вопрос')
    answer_text = models.TextField('Ответ пользователя')
    is_correct = models.BooleanField('Правильно?', default=False)

    def __str__(self):
        return f"{self.attempt.user.FIO} - {self.question.text[:30]}"

    class Meta:
        verbose_name = 'ответ'
        verbose_name_plural = 'Ответы'


class UserBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks', verbose_name='Пользователь')
    blocked_at = models.DateTimeField('Заблокирован', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает')
    reason = models.CharField('Причина', max_length=255, default='Проваленная аттестация')

    @property
    def is_active(self):
        return timezone.now() < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'блокировка'
        verbose_name_plural = 'Блокировки'


class Document(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название документа")
    description = models.TextField(blank=True, verbose_name="Описание")
    file = models.FileField(upload_to='documents/', verbose_name="PDF файл")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    created_by = models.ForeignKey('main_page.Admin', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Добавил")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    CATEGORY_CHOICES = [
        ('safety', 'Охрана труда'),
        ('fire', 'Пожарная безопасность'),
        ('instruction', 'Инструкция'),
        ('order', 'Приказ'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='safety', verbose_name="Категория")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentSignature(models.Model):
    user = models.ForeignKey('main_page.User', on_delete=models.CASCADE, related_name='document_signatures', verbose_name="Пользователь")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatures', verbose_name="Документ")
    signed_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата подписания")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP адрес")

    class Meta:
        unique_together = ['user', 'document']
        verbose_name = "Подпись"
        verbose_name_plural = "Подписи"

    def __str__(self):
        return f"{self.user.FIO} - {self.document.title}"


class VideoInspection(models.Model):
    STATUS_CHOICES = [
        ('queued', 'В очереди'),
        ('processing', 'Обрабатывается'),
        ('done', 'Готово'),
        ('failed', 'Ошибка'),
    ]

    inspector = models.ForeignKey(Inspector, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Инспектор')
    work_object = models.ForeignKey(WorkObject, on_delete=models.SET_NULL, null=True, blank=True, related_name='video_inspections', verbose_name='Заказ-наряд')
    camera = models.ForeignKey(Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections', verbose_name='Камера')
    object_number = models.CharField(max_length=150, blank=True, verbose_name='Зона выполнения работ')
    video = models.FileField(upload_to='inspections/videos/', verbose_name='Видео')
    check_helmet = models.BooleanField(default=True, verbose_name='Проверять каски')
    check_mask = models.BooleanField(default=False, verbose_name='Проверять маски')
    violation_seconds = models.FloatField(default=3.0, verbose_name='Порог нарушения (сек)')
    frame_stride = models.PositiveIntegerField(default=1, verbose_name='Шаг по кадрам')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', verbose_name='Статус')
    error = models.TextField(blank=True, default='', verbose_name='Текст ошибки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Старт обработки')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Окончание обработки')

    def __str__(self):
        return f"Проверка #{self.id} (объект {self.object_number})"

    class Meta:
        verbose_name = 'Проверка видео (СИЗ)'
        verbose_name_plural = 'Проверки видео (СИЗ)'
        ordering = ['-created_at']


class ViolationSnapshot(models.Model):
    VIOLATION_CHOICES = [
        ('no_helmet', 'Нет каски'),
        ('no_mask', 'Нет маски'),
        ('no_helmet_no_mask', 'Нет каски и маски'),
    ]

    inspection = models.ForeignKey(VideoInspection, on_delete=models.CASCADE, related_name='violations', verbose_name='Проверка')
    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ppe_violations', verbose_name='Сотрудник')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    timestamp_sec = models.FloatField(default=0.0, verbose_name='Время (сек)')
    frame_index = models.IntegerField(default=0, verbose_name='Кадр')
    person_track_id = models.IntegerField(default=0, verbose_name='ID человека (трек)')
    violation_type = models.CharField(max_length=30, choices=VIOLATION_CHOICES, verbose_name='Тип нарушения')
    conf_helmet = models.FloatField(null=True, blank=True, verbose_name='Уверенность (каска)')
    conf_mask = models.FloatField(null=True, blank=True, verbose_name='Уверенность (маска)')
    image = models.ImageField(upload_to='inspections/screenshots/', verbose_name='Скриншот')
    confirmed = models.BooleanField(null=True, blank=True, verbose_name='Подтверждено?')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Проверено')
    comment = models.TextField(blank=True, default='', verbose_name='Комментарий инспектора')

    def __str__(self):
        return f"Нарушение #{self.id} ({self.violation_type})"

    class Meta:
        verbose_name = 'Нарушение (скриншот)'
        verbose_name_plural = 'Нарушения (скриншоты)'
        ordering = ['-created_at']
