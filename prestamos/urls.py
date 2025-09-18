from django.urls import path
from . import views
from .views import PrestamoUpdateView


app_name = "prestamos"

urlpatterns = [
    path("trabajadores/", views.TrabajadorListView.as_view(), name="trabajador_list"),
    path("trabajadores/nuevo/", views.TrabajadorCreateView.as_view(), name="trabajador_create"),

    path("prestamos/", views.PrestamoListView.as_view(), name="prestamo_list"),
    path("prestamos/nuevo/", views.PrestamoCreateView.as_view(), name="prestamo_create"),
    path("prestamos/<int:pk>/", views.PrestamoDetailView.as_view(), name="prestamo_detail"),

    path("cancelar-cuotas-masivo/", views.cancelar_cuotas_masivo, name="cancelar_cuotas_masivo"),

    path("prestamo/<int:pk>/editar/", PrestamoUpdateView.as_view(), name="prestamo_edit"),

    path("prestamo/<int:pk>/pdf/", views.prestamo_pdf, name="prestamo_pdf"),

]
