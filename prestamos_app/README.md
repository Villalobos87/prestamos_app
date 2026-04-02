# Sistema de Préstamos (Django + PostgreSQL)

Proyecto base listo para correr. Registra trabajadores y préstamos, y genera automáticamente
el plan de pagos con cuotas fijas (principal + comisión prorrateada + interés fijo mensual).
Fechas alternan 15 y fin de mes.

## Requisitos
- Python 3.10+
- PostgreSQL (opcional para pruebas; por defecto usa SQLite)
- pip

## Instalación rápida
```bash
cd prestamos_app
python -m venv venv
venv\Scripts\activate  # Windows (PowerShell)
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # opcional
python manage.py runserver
```

Abre http://127.0.0.1:8000/

## Configurar PostgreSQL (recomendado)
Define variables de entorno antes de `runserver`:

- `POSTGRES_NAME`  (p.ej. empresa)
- `POSTGRES_USER`  (p.ej. postgres)
- `POSTGRES_PASSWORD` (tu contraseña)
- `POSTGRES_HOST`  (p.ej. localhost)
- `POSTGRES_PORT`  (p.ej. 5432)

Ejemplo (PowerShell):
```powershell
$env:POSTGRES_NAME="empresa"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="123456"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
```

Luego ejecuta:
```bash
python manage.py migrate
python manage.py runserver
```

## Qué incluye
- Modelos: Trabajador, Prestamo, Cuota
- Señal `post_save` que genera automáticamente las cuotas
- Lógica de fechas 15/fin de mes
- Vistas y formularios para:
    - Crear/listar Trabajadores
    - Crear/listar Préstamos
    - Detalle del préstamo con tabla de cuotas tipo Excel
- Admin de Django habilitado

## Notas de cálculo
- Interés mensual fijo: `interes%` del **monto** (constante para todas las cuotas).
- Principal por cuota: `monto / plazo`, ajustando la **última cuota** por redondeos.
- Comisión total: `comision%` del **monto**, prorrateada en el plazo (última cuota ajustada).
- Cuota = Principal_i + Comisión_i + InterésConstante.

Si deseas amortización sobre saldo (cuota decreciente), podemos ajustarlo luego.
