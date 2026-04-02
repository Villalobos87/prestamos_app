from django.db import models
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .utils import end_of_month, is_end_of_month, next_15_or_eom

TWO = Decimal('0.01')

class Trabajador(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=120)
    campus = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Prestamo(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, related_name="prestamos")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    interes = models.DecimalField(max_digits=5, decimal_places=2, help_text="% mensual, fijo")  # ej. 3.0 = 3%
    comision = models.DecimalField(max_digits=5, decimal_places=2, help_text="% total sobre monto")  # ej. 10.0 = 10%
    plazo = models.PositiveIntegerField(help_text="Número de cuotas/meses")
    fecha_inicio = models.DateField(help_text="Primera fecha de pago (15 o fin de mes)")
    fecha_final = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Préstamo {self.id} - {self.trabajador} ({self.plazo} meses)"

    def calcular_fijos(self):
        monto = Decimal(self.monto)
        interes_mensual = (monto * Decimal(self.interes) / Decimal('100')/2).quantize(TWO, rounding=ROUND_HALF_UP)
        interes_total = (monto * Decimal(self.interes) / Decimal("100") / 2 * Decimal(self.plazo)).quantize(TWO, rounding=ROUND_HALF_UP)
        comision_total = (monto * Decimal(self.comision) / Decimal('100')).quantize(TWO, rounding=ROUND_HALF_UP)
        principal_base = (monto / Decimal(self.plazo)).quantize(TWO, rounding=ROUND_HALF_UP)
        comision_base = (comision_total / Decimal(self.plazo)).quantize(TWO, rounding=ROUND_HALF_UP)
        return principal_base, comision_base, interes_mensual, comision_total,interes_total

    def generar_cuotas(self):
        """Regenera todas las cuotas del préstamo con fechas alternando 15 y fin de mes."""
        self.cuotas.all().delete()

        principal_base, comision_base, interes_base, comision_total, interes_total = self.calcular_fijos()

        # Ajustes de última cuota para cuadrar redondeos:
        monto = Decimal(self.monto)
        suma_principal = principal_base * Decimal(self.plazo - 1)
        ultimo_principal = (monto - suma_principal).quantize(TWO, rounding=ROUND_HALF_UP)

        suma_comision = comision_base * Decimal(self.plazo - 1)
        ultimo_comision = (comision_total - suma_comision).quantize(TWO, rounding=ROUND_HALF_UP)

        suma_interes = interes_base * Decimal(self.plazo - 1)
        ultimo_interes = (interes_total - suma_interes).quantize(TWO, rounding=ROUND_HALF_UP)


        # Normalizar primera fecha: si no es 15/EOM, llevar a 15 o EOM según regla
        f = self.fecha_inicio
        if f.day != 15 and not is_end_of_month(f):
            f = f.replace(day=15) if f.day <= 15 else end_of_month(f)

        for i in range(1, self.plazo + 1):
            principal_i = principal_base if i < self.plazo else ultimo_principal
            comision_i = comision_base if i < self.plazo else ultimo_comision
            interes_i   = interes_base if i < self.plazo else ultimo_interes
            total_i = (principal_i + comision_i + interes_i).quantize(TWO, rounding=ROUND_HALF_UP)

            Cuota.objects.create(
                prestamo=self,
                numero=i,
                principal=principal_i,
                comision=comision_i,
                interes=interes_i,
                monto_total=total_i,
                fecha_pago=f,
                estado="Pendiente",
            )
            f = next_15_or_eom(f)

        self.fecha_final = self.cuotas.order_by("numero").last().fecha_pago
        self.save(update_fields=["fecha_final"])


class Cuota(models.Model):
    ESTADOS = (
        ("Pendiente", "Pendiente"),
        ("Pagado", "Pagado"),
        ("Reprogramado", "Reprogramado"),
    )

    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="cuotas")
    numero = models.PositiveIntegerField()
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    comision = models.DecimalField(max_digits=12, decimal_places=2)
    interes = models.DecimalField(max_digits=12, decimal_places=2)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_pago = models.DateField()
    cheque = models.CharField(max_length=30, blank=True, default="")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="Pendiente")
    observacion = models.TextField(blank=True, default="")

    class Meta:
        unique_together = ("prestamo", "numero")
        ordering = ["numero"]

    def __str__(self):
        return f"Cuota {self.numero}/{self.prestamo.plazo} - {self.estado}"

    # === Métodos de gestión ===
    def aplicar_pago(self, cheque):
        """Marca la cuota como pagada asignando cheque."""
        self.cheque = cheque
        self.estado = "Pagado"
        self.save()

    def reprogramar(self, motivo=""):
        """Corre la fecha de pago a la siguiente quincena y agrega observación."""
        if self.estado == "Pendiente":
            self.fecha_pago = next_15_or_eom(self.fecha_pago)
            self.estado = "Reprogramado"
            self.observacion = motivo
            self.save()

    def sync_estado(self):
        """Asegura coherencia: si hay cheque => Pagado; si no => Pendiente."""
        if self.cheque:
            self.estado = "Pagado"
        elif self.estado != "Reprogramado":  # respetamos reprogramados
            self.estado = "Pendiente"
        self.save(update_fields=["estado"])