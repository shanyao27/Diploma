import re
from django import forms
from .models import User, Department, Position


class LoginForm(forms.Form):
    """Форма авторизации"""
    username = forms.CharField(
        label="Логин",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите логин'})
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )


class UserRegistrationForm(forms.ModelForm):
    """Форма регистрации сотрудника с автоматической генерацией логина"""

    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'})
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'})
    )

    class Meta:
        model = User
        fields = ['FIO', 'passportData', 'number', 'address', 'department', 'position', 'role']
        widgets = {
            'FIO': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'passportData': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234 567890'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+79991234567'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'г. Москва, ул. Ленина, д. 1'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'FIO': 'ФИО',
            'passportData': 'Паспорт',
            'number': 'Телефон',
            'address': 'Адрес',
            'department': 'Участок',
            'position': 'Штатная должность',
            'role': 'Роль в наряде',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].required = False
        self.fields['position'].required = False
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['position'].queryset = Position.objects.filter(is_active=True).order_by('name')

        if self.data.get('department'):
            self.fields['position'].queryset = Position.objects.filter(
                department_id=self.data.get('department'),
                is_active=True,
            ).order_by('name')

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')

        if password and password2 and password != password2:
            raise forms.ValidationError('Пароли не совпадают')
        return password2

    def clean_passportData(self):
        """Проверка уникальности паспорта"""
        passport = self.cleaned_data.get('passportData')
        if not passport:
            return passport

        passport_clean = passport.replace(' ', '')

        if User.objects.filter(passportData__icontains=passport_clean).exists():
            raise forms.ValidationError('Пользователь с таким паспортом уже зарегистрирован')
        return passport

    def clean_number(self):
        """Проверка уникальности номера телефона"""
        number = self.cleaned_data.get('number')
        if not number:
            return number

        number_clean = re.sub(r'[^\d]', '', number)

        if User.objects.filter(number__icontains=number_clean).exists():
            raise forms.ValidationError('Пользователь с таким номером телефона уже зарегистрирован')
        return number

    def generate_login(self, fio):
        """
        Генерирует логин из ФИО: Vdovenkov.NA
        Если такой логин уже существует, добавляет номер: Vdovenkov.NA1, Vdovenkov.NA2 и т.д.
        """
        parts = fio.strip().split()
        if len(parts) < 3:
            raise forms.ValidationError('ФИО должно содержать фамилию, имя и отчество')

        last_name = parts[0]
        first_name = parts[1]
        middle_name = parts[2]

        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
            'Ы': 'Y', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }

        translit_last = ''
        for char in last_name.lower():
            translit_last += translit_dict.get(char, char)

        translit_last = translit_last.capitalize()

        first_initial = translit_dict.get(first_name[0], first_name[0]).upper() if first_name else ''
        middle_initial = translit_dict.get(middle_name[0], middle_name[0]).upper() if middle_name else ''

        base_login = f"{translit_last}.{first_initial}{middle_initial}"

        login = base_login
        counter = 1

        while User.objects.filter(login=login).exists():
            login = f"{base_login}{counter}"
            counter += 1

        return login

    def save(self, commit=True):
        user = super().save(commit=False)
        user.login = self.generate_login(self.cleaned_data['FIO'])
        user.password = self.cleaned_data['password']
        user.isActive = False

        if commit:
            user.save()

            from profiles.models import Document
            all_docs = Document.objects.all()
            for doc in all_docs:
                if doc.id not in user.documents:
                    user.documents.append(doc.id)
            user.save()

        return user

class UserRegistrationForm(forms.ModelForm):
    passport_series = forms.CharField(label='Серия паспорта', max_length=4, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234', 'maxlength': 4}))
    passport_number = forms.CharField(label='Номер паспорта', max_length=6, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '567890', 'maxlength': 6}))
    number = forms.CharField(label='Телефон', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Введите пароль'}))
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}))

    class Meta:
        model = User
        fields = ['FIO', 'passport_series', 'passport_number', 'number', 'address', 'department']
        widgets = {
            'FIO': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'г. Москва, ул. Ленина, д. 1'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'FIO': 'ФИО',
            'address': 'Адрес',
            'department': 'Участок',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True).order_by('name')
        self.fields['department'].required = True
        if self.instance and self.instance.passportData:
            parts = re.sub(r'\D', '', self.instance.passportData)
            self.fields['passport_series'].initial = parts[:4]
            self.fields['passport_number'].initial = parts[4:10]

    def clean_password2(self):
        if self.cleaned_data.get('password') != self.cleaned_data.get('password2'):
            raise forms.ValidationError('Пароли не совпадают')
        return self.cleaned_data['password2']

    def clean_passport_series(self):
        value = re.sub(r'\D', '', self.cleaned_data.get('passport_series', ''))
        if len(value) != 4:
            raise forms.ValidationError('Серия паспорта должна содержать 4 цифры')
        return value

    def clean_passport_number(self):
        value = re.sub(r'\D', '', self.cleaned_data.get('passport_number', ''))
        if len(value) != 6:
            raise forms.ValidationError('Номер паспорта должен содержать 6 цифр')
        return value

    def clean_number(self):
        value = re.sub(r'\D', '', self.cleaned_data.get('number', ''))
        if value.startswith('8'):
            value = '7' + value[1:]
        if not value.startswith('7'):
            value = '7' + value
        if len(value) != 11:
            raise forms.ValidationError('Телефон должен содержать 11 цифр в формате РФ')
        normalized = '+' + value
        if User.objects.filter(number=normalized).exists():
            raise forms.ValidationError('Пользователь с таким номером телефона уже зарегистрирован')
        return normalized

    def clean(self):
        cleaned = super().clean()
        passport = f"{cleaned.get('passport_series', '')} {cleaned.get('passport_number', '')}".strip()
        if passport and User.objects.filter(passportData=passport).exists():
            self.add_error('passport_number', 'Пользователь с таким паспортом уже зарегистрирован')
        return cleaned

    def generate_login(self, fio):
        parts = fio.strip().split()
        if len(parts) < 3:
            raise forms.ValidationError('ФИО должно содержать фамилию, имя и отчество')
        last_name, first_name, middle_name = parts[:3]
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y',
            'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
            'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ы': 'y', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        translit_last = ''.join(translit_dict.get(ch.lower(), ch.lower()) for ch in last_name).capitalize()
        base_login = f"{translit_last}.{first_name[0].upper()}{middle_name[0].upper()}"
        login = base_login
        i = 1
        while User.objects.filter(login=login).exists():
            login = f"{base_login}{i}"
            i += 1
        return login

    def save(self, commit=True):
        user = super().save(commit=False)
        user.passportData = f"{self.cleaned_data['passport_series']} {self.cleaned_data['passport_number']}"
        user.role = 'worker'
        user.position = None
        user.login = self.generate_login(self.cleaned_data['FIO'])
        user.password = self.cleaned_data['password']
        user.isActive = False
        user.employment_status = 'pending'
        if commit:
            user.save()
            from profiles.models import Document
            for doc in Document.objects.all():
                if doc.id not in user.documents:
                    user.documents.append(doc.id)
            user.save(update_fields=['documents'])
        return user
