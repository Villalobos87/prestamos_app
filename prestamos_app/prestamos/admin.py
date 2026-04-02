from django.contrib import admin
from .models import Trabajador, Prestamo, Cuota

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "campus")
    search_fields = ("codigo", "nombre", "campus")

class CuotaInline(admin.TabularInline):
    model = Cuota
    extra = 0
    readonly_fields = ("numero", "principal", "comision", "interes", "monto_total", "fecha_pago", "estado", "cheque")

@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ("id", "trabajador", "monto", "interes", "comision", "plazo", "fecha_inicio", "fecha_final")
    inlines = [CuotaInline]

@admin.register(Cuota)
class CuotaAdmin(admin.ModelAdmin):
    list_display = ("prestamo", "numero", "fecha_pago", "monto_total", "estado")
    list_filter = ("estado",)
    search_fields = ("prestamo__trabajador__nombre",)
