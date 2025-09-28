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
from .models import Prestamo
from num2words import num2words
from datetime import datetime, timedelta


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
        # ⚠ Mensaje de error al usuario
        messages.error(request, "❌ BRUTA, TIENES QUE MARCAR LOS TRABAJADORES")
        return redirect("prestamos:cancelar_cuotas_masivo")

    cuotas = Cuota.objects.filter(pk__in=seleccionadas).select_related("prestamo", "prestamo__trabajador")


    # Tomamos fecha y campus de POST
    fecha = request.POST.get("fecha", "")
    campus = request.POST.get("campus", "")

    context = {
        "cuotas": cuotas,
        "total": sum(c.monto_total for c in cuotas),
        "fecha": fecha,
        "campus": campus,
    }

    html = render_to_string("prestamos/cuotas_masivo_pdf.html", context)

    pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(
        stylesheets=[CSS(string="""
            @page { size: A4; margin: 15mm; }
            body { font-family: Arial, sans-serif; font-size: 11px; color: #333; }
            h1 { text-align: center; margin-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { border: 1px solid #444; padding: 5px; text-align: center; }
            th { background: #f2f2f2; }
            tfoot td { font-weight: bold; background: #eaeaea; }
        """)]
    )

    # Formateamos fecha para el nombre del archivo
    fecha_texto = fecha.replace("-", "_") if fecha else "fecha"
    campus_texto = campus.upper() if campus else "TODOS"
    filename = f"Cuotas_{fecha_texto}_DEDUCCION_{campus_texto}.pdf"

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def prestamo_documento_pdf(request, pk, tipo):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    
    if tipo not in ["pagare"]:  # Solo afectar el Pagaré
        return HttpResponse("Tipo de documento inválido", status=400)

    # Meses en español
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Fecha de emisión
    hoy = datetime.today()
    fecha_texto = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

    # Traer todas las cuotas
    cuotas = Cuota.objects.filter(prestamo=prestamo).order_by("fecha_pago")
    numero_cuotas = cuotas.count() if cuotas.exists() else 1

    # Calcular el total (principal + comision + interes de todas las cuotas)
    totales = cuotas.aggregate(
        total_principal=Sum("principal"),
        total_comision=Sum("comision"),
        total_interes=Sum("interes"),
    )
    total_prestamo = (
        (totales["total_principal"] or 0) +
        (totales["total_comision"] or 0) +
        (totales["total_interes"] or 0)
    )

    # Calcular cuota quincenal
    cuota_quincenal = round(total_prestamo / numero_cuotas, 2)

    # Fechas de inicio y fin
    fecha_inicio_texto = (
        f"{cuotas.first().fecha_pago.day} de {meses[cuotas.first().fecha_pago.month - 1]} de {cuotas.first().fecha_pago.year}"
        if cuotas.exists() else ''
    )
    fecha_fin_texto = (
        f"{cuotas.last().fecha_pago.day} de {meses[cuotas.last().fecha_pago.month - 1]} de {cuotas.last().fecha_pago.year}"
        if cuotas.exists() else ''
    )

    # Monto en letras
    monto_letras = num2words(total_prestamo, lang="es").capitalize() + " dólares netos"

    context = {
        "prestamo": prestamo,
        "trabajador": prestamo.trabajador,
        "fecha_texto": fecha_texto,
        "ciudad": prestamo.trabajador.campus,
        "monto_total": total_prestamo,        # <<-- ya suma 366
        "monto_letras": monto_letras,
        "cuota_quincenal": cuota_quincenal,   # <<-- 45.75
        "fecha_inicio_texto": fecha_inicio_texto,
        "fecha_fin_texto": fecha_fin_texto,
    }

    # Renderizar template del Pagaré
    html_string = render_to_string("prestamos/pdf_pagare.html", context)

    pdf_file = HTML(string=html_string).write_pdf(
        stylesheets=[CSS(string="""
            @page { size: A4 landscape; margin: 20mm; }
            body { font-family: Arial, sans-serif; font-size: 12px; line-height: 1.6; }
            h1, h2, h3 { text-align: center; }
            .firma { margin-top: 50px; text-align: center; }
        """)]
    )

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename=pagare_prestamo_{prestamo.id}.pdf'
    return response

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.http import HttpResponse
from decimal import Decimal
from num2words import num2words
from datetime import date
import weasyprint

def imprimir_documento(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id)
    tipo = request.GET.get("tipo")

    if tipo not in ["solicitud", "recibo", "pagare"]:
        return HttpResponse("❌ Tipo de documento inválido", status=400)

    # Meses en español
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]

    # Fecha de emisión
    hoy = datetime.today()
    fecha_texto = f"{hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

    # Obtener cuotas relacionadas (ordenadas por fecha)
    cuotas = prestamo.cuotas.all().order_by('fecha_pago')
    numero_cuotas = cuotas.count() if cuotas.exists() else 1

    # =========================
    # Monto total: para pagaré sumar todas las cuotas (principal + comision + interes)
    # =========================
    if tipo == "pagare":
        totales = cuotas.aggregate(
            total_principal=Sum("principal"),
            total_comision=Sum("comision"),
            total_interes=Sum("interes"),
        )
        tp = totales.get("total_principal") or Decimal("0")
        tc = totales.get("total_comision") or Decimal("0")
        ti = totales.get("total_interes") or Decimal("0")

        # Asegurar Decimal y redondeo a 2 decimales
        monto_total = (Decimal(tp) + Decimal(tc) + Decimal(ti)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        # Para solicitud/recibo usare el monto guardado en Prestamo
        monto_total = Decimal(prestamo.monto).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # =========================
    # Calcular cuota quincenal (total / número de cuotas)
    # =========================
    cuota_quincenal = (monto_total / Decimal(numero_cuotas)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # =========================
    # Fechas inicio y fin (usar primera y última cuota reales si existen)
    # =========================
    if cuotas.exists():
        fecha_inicio = cuotas.first().fecha_pago
        fecha_fin = cuotas.last().fecha_pago
        fecha_inicio_texto = f"{fecha_inicio.day} de {meses[fecha_inicio.month - 1]} de {fecha_inicio.year}"
        fecha_fin_texto = f"{fecha_fin.day} de {meses[fecha_fin.month - 1]} de {fecha_fin.year}"
    else:
        fecha_inicio_texto = fecha_texto
        fecha_fin_texto = fecha_texto

    # =========================
    # Monto en letras (manejo de centavos)
    # =========================
    entero = int(monto_total)
    centavos = int((monto_total - Decimal(entero)) * 100)
    if centavos:
        letras = f"{num2words(entero, lang='es').upper()} CON {num2words(centavos, lang='es').upper()} CENTAVOS DÓLARES NETOS"
    else:
        letras = f"{num2words(entero, lang='es').upper()} DÓLARES NETOS"

    # =========================
    # Contexto y render
    # =========================
    context = {
        "prestamo": prestamo,
        "trabajador": prestamo.trabajador,
        "fecha_texto": fecha_texto,
        "ciudad": prestamo.trabajador.campus,
        "monto_total": monto_total,               # numérico: Decimal('366.00')
        "monto_letras": letras,                   # texto: "TRESCIENTOS SESENTA Y SEIS DÓLARES NETOS"
        "cuota_quincenal": cuota_quincenal,       # Decimal('45.75')
        "fecha_inicio_texto": fecha_inicio_texto,
        "fecha_fin_texto": fecha_fin_texto,
        "numero_cuotas": numero_cuotas,
    }

    # Renderizar template del documento correcto (usa pdf_pagare.html, pdf_recibo.html, etc.)
    html_string = render_to_string(f"prestamos/pdf_{tipo}.html", context)

    # Mantener vertical (portrait) como pediste
    css = CSS(string="@page { size: A4 portrait; margin: 20mm; } body { font-family: Arial, sans-serif; font-size: 12px; }")

    pdf_file = HTML(string=html_string).write_pdf(stylesheets=[css])

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename={tipo}_prestamo_{prestamo.id}.pdf'
    return response