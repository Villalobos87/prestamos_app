from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home(_):
    return redirect("prestamos:prestamo_list")

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("", include("prestamos.urls")),
]
