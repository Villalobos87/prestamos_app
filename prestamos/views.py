from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.contrib import messages
from .models import Trabajador, Prestamo, Cuota
from .forms import TrabajadorForm, PrestamoForm
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from .filters import TrabajadorFilter, PrestamoFilter
from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint
import tempfile
from django.db.models import Sum
from io import BytesIO
from django.conf import settings
import os
from weasyprint import HTML, CSS



# ======================================
# Trabajador Views
# ======================================
class TrabajadorListView(ListView):
    model = Trabajador
    template_name = "prestamos/trabajador_list.html"
    context_object_name = "items"
    filterset_class = TrabajadorFilter


class TrabajadorCreateView(CreateView):
    model = Trabajador
    form_class = TrabajadorForm
    success_url = reverse_lazy("prestamos:trabajador_list")
    template_name = "prestamos/trabajador_form.html"


# ======================================
# Prestamo Views
# ======================================
class PrestamoListView(ListView):
    model = Prestamo
    template_name = "prestamos/prestamo_list.html"
    context_object_name = "items"
    queryset = Prestamo.objects.select_related("trabajador").all()
    ordering = ['-id']
    filterset_class = PrestamoFilter


# ======================================
# Función para generar cuotas
# ======================================
def generar_cuotas(prestamo):
    # Eliminar cuotas existentes
    prestamo.cuotas.all().delete()

    monto_total = Decimal(prestamo.monto)
    plazo = prestamo.plazo
    interes_fijo = (monto_total * Decimal(prestamo.interes) / 100/2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    comision_total = (monto_total * Decimal(prestamo.comision) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    comision_por_cuota = (comision_total / plazo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    capital_por_cuota = (monto_total / plazo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    fecha = prestamo.fecha_inicio

    for n in range(1, plazo + 1):
        # Alternar día 15 y último día del mes
        if fecha.day <= 15:
            dia = 15
        else:
            dia = monthrange(fecha.year, fecha.month)[1]

        # Crear la fecha de la cuota
        cuota_fecha = fecha.replace(day=dia)

        # Ajustar última cuota
        if n == plazo:
            capital_cuota_final = (monto_total - capital_por_cuota * (plazo - 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            comision_cuota_final = (comision_total - comision_por_cuota * (plazo - 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            capital_cuota_final = capital_por_cuota
            comision_cuota_final = comision_por_cuota

        monto_cuota = (capital_cuota_final + interes_fijo + comision_cuota_final).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        Cuota.objects.create(
            prestamo=prestamo,
            numero=n,
            principal=float(capital_cuota_final),
            interes=float(interes_fijo),
            comision=float(comision_cuota_final),
            monto_total=float(monto_cuota),
            fecha_pago=cuota_fecha,
            estado="Pendiente",
        )

        # Alternamos fecha para la siguiente cuota
        if dia == 15:
            fecha = fecha.replace(day=monthrange(fecha.year, fecha.month)[1])  # fin de mes
        else:
            fecha += relativedelta(months=1)
            fecha = fecha.replace(day=15)  # siguiente 15


# ======================================
# Crear Prestamo
# ======================================
class PrestamoCreateView(CreateView):
    model = Prestamo
    form_class = PrestamoForm
    template_name = "prestamos/prestamo_form.html"

    def get_initial(self):
        initial = super().get_initial()
        initial['interes'] = 3
        initial['comision'] = 10

        # Plazo por defecto según monto (si existe en GET)
        monto = self.request.GET.get('monto')
        try:
            if monto:
                monto = float(monto)
                if monto <= 50: initial['plazo'] = 4
                elif monto <= 100: initial['plazo'] = 6
                elif monto <= 150: initial['plazo'] = 6
                elif monto <= 200: initial['plazo'] = 7
                elif monto <= 250: initial['plazo'] = 7
                elif monto <= 300: initial['plazo'] = 8
                elif monto <= 350: initial['plazo'] = 9
                elif monto <= 400: initial['plazo'] = 10
                elif monto <= 450: initial['plazo'] = 11
                elif monto <= 500: initial['plazo'] = 11
                else: initial['plazo'] = 12
        except:
            pass
        return initial

    def get_success_url(self):
        return reverse_lazy("prestamos:prestamo_detail", kwargs={"pk": self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        generar_cuotas(self.object)
        return response


# ======================================
# Detalle Prestamo
# ======================================
class PrestamoDetailView(DetailView):
    model = Prestamo
    template_name = "prestamos/prestamo_detail.html"

    def get_queryset(self):
        return Prestamo.objects.select_related("trabajador").prefetch_related("cuotas")

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        cuota_id = request.POST.get("cuota_id")
        accion = request.POST.get("accion")
        cheque = request.POST.get("cheque", "").strip()
        nueva_fecha = request.POST.get("nueva_fecha", "").strip()
        motivo = request.POST.get("motivo", "").strip()

        cuota = get_object_or_404(Cuota, pk=cuota_id, prestamo=self.object)

        if accion == "pagar":
            if cuota.estado == "Pagado":
                messages.info(request, f"ℹ La cuota {cuota.numero} ya estaba marcada como pagada.")
            else:
                cuota.estado = "Pagado"
                if cheque:
                    cuota.cheque = cheque
                cuota.save(update_fields=["estado", "cheque"])
                messages.success(request, f"✅ Cuota {cuota.numero} marcada como pagada.")
        elif accion == "modificar_fecha":
            if cuota.estado == "Pagado":
                messages.error(request, f"❌ No se puede modificar la fecha de la cuota {cuota.numero} porque ya está pagada.")
            else:
                if nueva_fecha:
                    cuota.fecha_pago = nueva_fecha
                    cuota.save(update_fields=["fecha_pago"])
                    messages.warning(request, f"↪ Fecha de cuota {cuota.numero} cambiada a {nueva_fecha}.")
                else:
                    messages.error(request, "❌ No ingresaste la nueva fecha.")
        else:
            messages.error(request, "Acción no válida.")

        return redirect("prestamos:prestamo_detail", pk=self.object.pk)


# ======================================
# Editar Prestamo
# ======================================
class PrestamoUpdateView(UpdateView):
    model = Prestamo
    form_class = PrestamoForm
    template_name = "prestamos/prestamo_form.html"

    def get_success_url(self):
        return reverse_lazy("prestamos:prestamo_detail", kwargs={"pk": self.object.pk})

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        # 🔹 Primero eliminamos las cuotas viejas
        self.object.cuotas.all().delete()

        # 🔹 Generamos nuevamente las cuotas con el nuevo plazo/monto
        generar_cuotas(self.object)

        # 🔹 Actualizamos la fecha final al último pago
        ultima_cuota = self.object.cuotas.order_by("-fecha_pago").first()
        if ultima_cuota:
            self.object.fecha_final = ultima_cuota.fecha_pago
            self.object.save(update_fields=["fecha_final"])

        return response


# ======================================
# Cancelar / Modificar Cuotas Masivas
# ======================================
@transaction.atomic
def cancelar_cuotas_masivo(request):
    cuotas = []
    total = 0
    mensaje_info = ""

    if request.method == "POST":
        seleccionadas = request.POST.getlist("cuotas")
        accion = request.POST.get("accion")
        cheque_valor = request.POST.get("cheque", "").strip()
        nueva_fecha = request.POST.get("nueva_fecha", "").strip()
        observacion = request.POST.get("observacion", "").strip()

        if seleccionadas:
            cuotas_seleccionadas = Cuota.objects.filter(pk__in=seleccionadas, estado="Pendiente")
            total_seleccionado = sum(c.monto_total for c in cuotas_seleccionadas)
            mensaje_info = f"⚠ Se van a procesar {cuotas_seleccionadas.count()} cuota(s) con un total pendiente de ${total_seleccionado:.2f}."

            # Mostramos mensaje informativo antes de aplicar acción
            messages.info(request, mensaje_info)

            for cuota in cuotas_seleccionadas:
                if accion == "cancelar":
                    cuota.estado = "Pagado"
                    if cheque_valor:
                        cuota.cheque = cheque_valor
                    cuota.save(update_fields=["estado", "cheque"])
                elif accion == "modificar_fecha":
                    if nueva_fecha:
                        cuota.fecha_pago = nueva_fecha
                        cuota.motivo = observacion
                        cuota.save(update_fields=["fecha_pago"])
            messages.success(request, "✅ Acciones aplicadas a las cuotas seleccionadas.")
            return redirect("prestamos:cancelar_cuotas_masivo")
        else:
            messages.error(request, "❌ No seleccionaste ninguna cuota.")

    # ===================
    # Filtro GET
    # ===================
    fecha = request.GET.get("fecha")
    campus = request.GET.get("campus", "")
    if fecha:
        cuotas = Cuota.objects.filter(fecha_pago=fecha, estado="Pendiente")
        if campus:
            cuotas = cuotas.filter(prestamo__trabajador__campus=campus)
        cuotas = cuotas.select_related("prestamo", "prestamo__trabajador")
        total = sum(c.monto_total for c in cuotas)
    else:
        cuotas = []
        total = 0

    return render(
        request,
        "prestamos/cancelar_cuotas_masivo.html",
        {
            "cuotas": cuotas,
            "fecha": fecha,
            "campus": campus,
            "total": total,
        }
    )

    # ===================
    # Filtro GET
    # ===================
    fecha = request.GET.get("fecha")
    campus = request.GET.get("campus", "")
    if fecha:
        cuotas = Cuota.objects.filter(fecha_pago=fecha, estado="Pendiente")
        if campus:
            cuotas = cuotas.filter(prestamo__trabajador__campus=campus)
        cuotas = cuotas.select_related("prestamo", "prestamo__trabajador")
        total = sum(c.monto_total for c in cuotas)
    else:
        cuotas = []
        total = 0

    return render(
        request,
        "prestamos/cancelar_cuotas_masivo.html",
        {
            "cuotas": cuotas,
            "fecha": fecha,
            "campus": campus,
            "total": total,
        }
    )

def prestamo_pdf(request, pk):
    prestamo = Prestamo.objects.get(pk=pk)
    html = render_to_string("prestamos/prestamo_pdf.html", {"object": prestamo})

    pdf_file = HTML(string=html).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"Prestamo_{prestamo.id}_{prestamo.trabajador.nombre}_{prestamo.trabajador.campus}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def cuotas_masivo_pdf(request):
    seleccionadas = request.POST.getlist("cuotas")

    if not seleccionadas:
        messages.error(request, "❌ No seleccionaste ninguna cuota.")
        return redirect("prestamos:cancelar_cuotas_masivo")

    cuotas = Cuota.objects.filter(pk__in=seleccionadas).select_related("prestamo", "prestamo__trabajador")

    context = {
        "cuotas": cuotas,
        "total": sum(c.monto_total for c in cuotas),
    }

    html = render_to_string("prestamos/cuotas_masivo_pdf.html", context)

    pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(
        stylesheets=[CSS(string="""
            @page {
                size: A4;
                margin: 15mm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11px;
                color: #333;
            }
            h1 {
                text-align: center;
                margin-bottom: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }
            th, td {
                border: 1px solid #444;
                padding: 5px;
                text-align: center;
            }
            th {
                background: #f2f2f2;
            }
            tfoot td {
                font-weight: bold;
                background: #eaeaea;
            }
        """)]
    )

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = 'attachment; filename="Cuotas_Seleccionadas.pdf"'
    return response




