# Generated manually on 2026-03-30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_page', '0011_department_admin_full_name_admin_is_global_admin_and_more'),
        ('profiles', '0010_violationtype_workobject_actual_end_time_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='certificationtest',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='certification_tests', to='main_page.department', verbose_name='Участок'),
        ),
        migrations.AddField(
            model_name='medicalcheck',
            name='sanction_reason',
            field=models.CharField(blank=True, max_length=255, verbose_name='Основание'),
        ),
        migrations.AddField(
            model_name='medicalcheck',
            name='sanction_type',
            field=models.CharField(blank=True, choices=[('warning', 'Предупреждение'), ('explanation', 'Объяснительная'), ('fine', 'Штраф / лишение премии'), ('suspension', 'Отстранение'), ('dismissal_notice', 'Уведомление на увольнение')], max_length=30, verbose_name='Санкция'),
        ),
        migrations.AddField(
            model_name='workobject',
            name='close_grace_minutes',
            field=models.PositiveIntegerField(default=60, verbose_name='Допустимая просрочка закрытия (мин)'),
        ),
        migrations.AlterField(
            model_name='medicalcheck',
            name='decision',
            field=models.CharField(choices=[('fit', 'Допущен'), ('unfit', 'Не допущен')], max_length=20, verbose_name='Решение'),
        ),
        migrations.AlterField(
            model_name='videoinspection',
            name='object_number',
            field=models.CharField(blank=True, max_length=150, verbose_name='Зона выполнения работ'),
        ),
        migrations.AlterField(
            model_name='workobject',
            name='address',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='Адрес'),
        ),
    ]
