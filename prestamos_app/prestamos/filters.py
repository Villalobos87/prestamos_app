import django_filters
from .models import Trabajador, Prestamo

class TrabajadorFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(lookup_expr="icontains", label="Nombre")
    campus = django_filters.CharFilter(lookup_expr="icontains", label="Campus")

    class Meta:
        model = Trabajador
        fields = ["nombre", "campus"]


class PrestamoFilter(django_filters.FilterSet):
    trabajador = django_filters.CharFilter(field_name="trabajador__nombre", lookup_expr="icontains", label="Trabajador")
    estado = django_filters.CharFilter(field_name="cuotas__estado", lookup_expr="icontains", label="Estado")

    class Meta:
        model = Prestamo
        fields = ["trabajador", "estado"]