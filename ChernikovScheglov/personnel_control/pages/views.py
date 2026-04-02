from django.shortcuts import render


def page_not_found(request, exception):
    template_html = 'pages/404.html'
    return render(request, template_html, status=404)


def permission_denied(request, exception):
    template_html = 'pages/403csrf.html'
    return render(request, template_html, status=403)


def server_error(request):
    tempate_html = 'pages/500.html'
    return render(request, tempate_html, status=500)
