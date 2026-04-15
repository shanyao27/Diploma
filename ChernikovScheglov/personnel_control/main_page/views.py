from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import LoginForm, UserRegistrationForm
from .models import User, Admin, Inspector, Medic


def main_page(request):
    return render(request, 'main_page/main_page.html')


def about(request):
    return render(request, 'main_page/about.html')


def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Проверка User
            try:
                user = User.objects.get(login=username)
                if user.check_password(password):  # ✅ Правильно
                    request.session['user_id'] = user.id
                    request.session['user_login'] = user.login

                    if user.system_role == 'medic':
                        request.session['user_role'] = 'medic'
                    elif user.system_role == 'inspector':
                        request.session['user_role'] = 'inspector'
                    elif user.system_role in ['manager', 'global_admin']:
                        request.session['user_role'] = 'admin'
                    else:
                        request.session['user_role'] = 'user'

                    return redirect('profiles:dashboard')
            except User.DoesNotExist:
                pass

            try:
                medic = Medic.objects.get(login=username, isActive=True)
                if medic.check_password(password):
                    request.session['user_id'] = medic.id
                    request.session['user_login'] = medic.login
                    request.session['user_role'] = 'medic'
                    return redirect('profiles:dashboard')
            except Medic.DoesNotExist:
                pass

            # Проверка Admin - ИСПРАВЛЕНО!
            try:
                admin = Admin.objects.get(login=username, isActive=True)
                if admin.check_password(password):  # ✅ ИСПРАВЛЕНО!
                    request.session['user_id'] = admin.id
                    request.session['user_login'] = admin.login
                    request.session['user_role'] = 'admin'
                    return redirect('profiles:dashboard')
            except Admin.DoesNotExist:
                pass

            # Проверка Inspector - ИСПРАВЛЕНО!
            try:
                inspector = Inspector.objects.get(login=username, isActive=True)
                if inspector.check_password(password):  # ✅ ИСПРАВЛЕНО!
                    request.session['user_id'] = inspector.id
                    request.session['user_login'] = inspector.login
                    request.session['user_role'] = 'inspector'
                    return redirect('profiles:dashboard')
            except Inspector.DoesNotExist:
                pass

            return render(request, 'main_page/login.html', {
                'form': form,
                'error': 'Неверный логин или пароль'
            })
    else:
        form = LoginForm()

    return render(request, 'main_page/login.html', {'form': form})


def registration(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            messages.success(
                request,
                f'Регистрация успешна! Ваш логин для авторизации: {user.login}'
            )

            messages.success(
                request,
                'Дождитесь подтверждения администратора'
            )
            
            return redirect('main_page:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'main_page/registration.html', {'form': form})