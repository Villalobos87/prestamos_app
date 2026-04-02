from django.contrib import admin
from django.urls import path, include
from prestamos import views as prestamos_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ rutas de login/logout sin namespace
    path('login/', prestamos_views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='prestamos:login'), name='logout'),

    # ✅ incluye todas las URLs de préstamos
    path('', include('prestamos.urls')),
]