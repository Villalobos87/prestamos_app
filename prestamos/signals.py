from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Prestamo

@receiver(post_save, sender=Prestamo)
def generar_cuotas_post_save(sender, instance: Prestamo, created, **kwargs):
    # Solo generar al crear; si se desea regenerar al editar, podemos controlar con una bandera
    if created:
        instance.generar_cuotas()
