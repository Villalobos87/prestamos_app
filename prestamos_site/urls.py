from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

# Redirigir la raíz "/" al login
def home_redirect(request):
    return redirect('prestamos:login')

urlpatterns = [
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('', include('prestamos.urls')),
]