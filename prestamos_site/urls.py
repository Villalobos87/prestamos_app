from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

# Redirige la raíz al login
def home_redirect(request):
    return redirect('prestamos:login')  # namespace 'prestamos' + name 'login'

urlpatterns = [
    path('', home_redirect, name='home'),       # raíz
    path('admin/', admin.site.urls),            # admin
    path('', include('prestamos.urls', namespace='prestamos')),  # incluye app con namespace
]