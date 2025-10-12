from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home_redirect(request):
    return redirect("prestamos:login")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_redirect, name="home"),  # raíz redirige al login
    path("", include("prestamos.urls")),   # incluye las rutas de la app
]