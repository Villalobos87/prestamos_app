from django.contrib import admin
from django.urls import path, include
from prestamos import views as prestamos_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔐 AUTH (login / logout)
    path('', prestamos_views.login_view, name='login'),  # 👈 login en raíz
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 💰 MÓDULO PRÉSTAMOS
    path('prestamos/', include('prestamos.urls')),

    # 🚗 MÓDULO ESCUELA (tasks)
    path('escuela/', include('tasks.urls')),
]