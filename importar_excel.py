import os
import django
import pandas as pd
from decimal import Decimal
from datetime import datetime

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "prestamos_site.settings")
django.setup()

from prestamos.models import Trabajador, Prestamo

# Leer el Excel
df = pd.read_excel("prestamos_importar.xlsx")  # columnas: monto, interes, comision, plazo, fecha_inicio, trabajador_id

for index, row in df.iterrows():
    try:
        trabajador = Trabajador.objects.get(id=int(row['trabajador_id']))
    except Trabajador.DoesNotExist:
        print(f"Trabajador con ID {row['trabajador_id']} no existe. Se omite este préstamo.")
        continue

    # Crear el préstamo
    prestamo = Prestamo.objects.create(
        trabajador=trabajador,
        monto=Decimal(row['monto']),
        interes=Decimal(row['interes']),
        comision=Decimal(row['comision']),
        plazo=int(row['plazo']),
        fecha_inicio = pd.to_datetime(row['fecha_inicio']).date()
    )

    # Generar automáticamente las cuotas
    prestamo.generar_cuotas()

print("Importación completada. Se crearon los préstamos y sus cuotas automáticamente.")

# python importar_excel.py                          (Codigo para importar)