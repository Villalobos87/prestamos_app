from django import forms
from .models import Trabajador, Prestamo

class TrabajadorForm(forms.ModelForm):

    CAMPUS_CHOICES = [
        ('LEÓN', 'LEÓN'),
        ('MATAGALPA', 'MATAGALPA'),
        ('MANAGUA', 'MANAGUA'),
    ]

    campus = forms.ChoiceField(
        choices=CAMPUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = Trabajador

        fields = [
            'codigo',
            'nombre',
            'campus',
            'cuenta_bancaria_cordobas',
            'cuenta_bancaria_dolares',
        ]

        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el código'
            }),

            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre completo'
            }),

            'cuenta_bancaria_cordobas': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta en córdobas'
            }),

            'cuenta_bancaria_dolares': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cuenta en dólares'
            }),
        }

        labels = {
            'codigo': 'Código',
            'nombre': 'Nombre completo',
            'campus': 'Campus',
            'cuenta_bancaria_cordobas': 'Cuenta bancaria en córdobas (C$)',
            'cuenta_bancaria_dolares': 'Cuenta bancaria en dólares (US$)',
        }

class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ["trabajador", "monto", "interes", "comision", "plazo", "fecha_inicio"]
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            }

class SeleccionQuincenaForm(forms.Form):
    campus = forms.ChoiceField(choices=[], label="Campus")
    fecha_pago = forms.DateField(widget=forms.SelectDateWidget)
    cheque = forms.CharField(max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # choices dinámicos desde los trabajadores
        self.fields["campus"].choices = [
            (c, c) for c in Trabajador.objects.values_list("campus", flat=True).distinct()
        ]

        

        
