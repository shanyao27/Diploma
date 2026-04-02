from django.core.management.base import BaseCommand
from main_page.models import Department, Position
from profiles.models import Camera, ViolationType


DEPARTMENTS = [
    ('kip', 'Участок КИП', 'Контрольно-измерительные приборы и автоматика'),
    ('electro', 'Электротехнический участок', 'Эксплуатация и ремонт электрооборудования'),
    ('garage', 'Транспортный участок', 'Водители, механики, транспорт'),
    ('medical', 'Медпункт', 'Предрейсовые и послесменные осмотры'),
    ('safety', 'Служба ОТ и ПБ', 'Охрана труда и промышленная безопасность'),
    ('mechanic', 'Механический участок', 'Ремонт и обслуживание оборудования'),
]

POSITIONS = {
    'kip': ['Слесарь КИПиА', 'Инженер КИПиА', 'Мастер КИПиА', 'Начальник участка КИП'],
    'electro': ['Электромонтер', 'Инженер-электрик', 'Мастер участка', 'Начальник электроучастка'],
    'garage': ['Водитель', 'Механик', 'Диспетчер транспорта', 'Начальник гаража'],
    'medical': ['Фельдшер', 'Медсестра', 'Врач', 'Заведующий медпунктом'],
    'safety': ['Инспектор по охране труда', 'Инженер по промышленной безопасности', 'Начальник службы ОТ и ПБ'],
    'mechanic': ['Слесарь-ремонтник', 'Токарь', 'Мастер механического участка', 'Начальник механического участка'],
}

CAMERAS = {
    'kip': ['КИП-01 Щитовая', 'КИП-02 Насосная'],
    'electro': ['ЭЛ-01 Подстанция', 'ЭЛ-02 РУ-6кВ'],
    'garage': ['ГАР-01 Въезд', 'ГАР-02 Ремзона'],
    'safety': ['ОТ-01 Склад СИЗ', 'ОТ-02 Общая проходная'],
    'mechanic': ['МЕХ-01 Цех', 'МЕХ-02 Участок сварки'],
}

VIOLATIONS = [
    ('Пропуск утреннего медосмотра', 'medical', 'medium', 'explanation'),
    ('Не допущен по результатам осмотра', 'medical', 'high', 'suspension'),
    ('Неявка на наряд', 'work_order', 'medium', 'warning'),
    ('Просрочка закрытия наряда', 'work_order', 'medium', 'explanation'),
    ('Повторный срыв срока наряда', 'work_order', 'high', 'fine'),
    ('Отсутствие каски', 'ppe', 'high', 'fine'),
    ('Отсутствие маски', 'ppe', 'medium', 'warning'),
    ('Грубое нарушение требований СИЗ', 'ppe', 'critical', 'dismissal_notice'),
    ('Нарушение трудовой дисциплины', 'discipline', 'medium', 'warning'),
]


class Command(BaseCommand):
    help = 'Заполняет проект базовыми участками, должностями, камерами и типами нарушений.'

    def handle(self, *args, **options):
        dep_map = {}

        for code, name, description in DEPARTMENTS:
            dep = Department.objects.filter(code=code).first()

            if dep is None:
                dep = Department.objects.filter(name=name).first()

            if dep is None:
                dep = Department.objects.create(
                    code=code,
                    name=name,
                    description=description,
                    is_active=True
                )
            else:
                changed = False

                if dep.code != code:
                    dep.code = code
                    changed = True

                if dep.name != name:
                    dep.name = name
                    changed = True

                if dep.description != description:
                    dep.description = description
                    changed = True

                if not dep.is_active:
                    dep.is_active = True
                    changed = True

                if changed:
                    dep.save()

            dep_map[code] = dep

        for code, positions in POSITIONS.items():
            dep = dep_map[code]

            for position_name in positions:
                is_managerial = (
                    'Начальник' in position_name
                    or 'Мастер' in position_name
                    or 'Заведующий' in position_name
                )

                position, created = Position.objects.get_or_create(
                    department=dep,
                    name=position_name,
                    defaults={
                        'is_managerial': is_managerial,
                        'requires_medical_check': True,
                        'is_active': True,
                    },
                )

                changed = False
                if position.is_managerial != is_managerial:
                    position.is_managerial = is_managerial
                    changed = True
                if not position.requires_medical_check:
                    position.requires_medical_check = True
                    changed = True
                if not position.is_active:
                    position.is_active = True
                    changed = True

                if changed:
                    position.save()

        for code, cameras in CAMERAS.items():
            dep = dep_map[code]

            for camera_name in cameras:
                zone = camera_name.split(' ', 1)[-1] if ' ' in camera_name else camera_name

                camera, created = Camera.objects.get_or_create(
                    department=dep,
                    name=camera_name,
                    defaults={
                        'zone': zone,
                        'is_active': True
                    },
                )

                changed = False
                if camera.zone != zone:
                    camera.zone = zone
                    changed = True
                if not camera.is_active:
                    camera.is_active = True
                    changed = True

                if changed:
                    camera.save()

        for name, category, severity, default_sanction in VIOLATIONS:
            violation, created = ViolationType.objects.get_or_create(
                name=name,
                defaults={
                    'category': category,
                    'severity': severity,
                    'default_sanction': default_sanction,
                    'is_active': True,
                },
            )

            changed = False
            if violation.category != category:
                violation.category = category
                changed = True
            if violation.severity != severity:
                violation.severity = severity
                changed = True
            if violation.default_sanction != default_sanction:
                violation.default_sanction = default_sanction
                changed = True
            if not violation.is_active:
                violation.is_active = True
                changed = True

            if changed:
                violation.save()

        self.stdout.write(self.style.SUCCESS('Базовые справочники предприятия заполнены.'))