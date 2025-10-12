from django.urls import path
from . import views
from .views import PrestamoUpdateView, cuotas_masivo_pdf
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from .views import login_view

app_name = "prestamos"  # namespace

# Redirección a login desde la raíz de la app
def home_redirect(request):
    return redirect("prestamos:login")

urlpatterns = [
    # Trabajadores
    path("trabajadores/", views.TrabajadorListView.as_view(), name="trabajador_list"),
    path("trabajadores/nuevo/", views.TrabajadorCreateView.as_view(), name="trabajador_create"),

    # Préstamos
    path("prestamos/", views.PrestamoListView.as_view(), name="prestamo_list"),
    path("prestamos/nuevo/", views.PrestamoCreateView.as_view(), name="prestamo_create"),
    path("prestamos/<int:pk>/", views.PrestamoDetailView.as_view(), name="prestamo_detail"),
    path("prestamo/<int:pk>/editar/", PrestamoUpdateView.as_view(), name="prestamo_edit"),

    # PDFs y documentos
    path("prestamo/<int:pk>/pdf/", views.prestamo_pdf, name="prestamo_pdf"),
    path("prestamo/<int:pk>/pdf/<str:tipo>/", views.prestamo_documento_pdf, name="prestamo_documento_pdf"),
    path("cuotas/pdf/", cuotas_masivo_pdf, name="cuotas_masivo_pdf"),
    path("<int:prestamo_id>/imprimir/", views.imprimir_documento, name="imprimir_documento"),
    path("prestamo/<int:pk>/enviar_correo/", views.enviar_correo, name="enviar_correo"),

    # Cancelar cuotas
    path("cancelar-cuotas-masivo/", views.cancelar_cuotas_masivo, name="cancelar_cuotas_masivo"),

    # Login y Logout
    path('accounts/login/', login_view, name='login'),
    path("logout/", auth_views.LogoutView.as_view(next_page="prestamos:login"), name="logout"),

    # Redirección raíz de la app
    path("", home_redirect, name="home_redirect"),
]