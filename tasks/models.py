from django.db import models


# Create your models here.

class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    hora = models.TimeField(null=True, blank=True)
    instructor = models.CharField(max_length=100, blank=True, null=True)  # ahora es texto
    completado = models.BooleanField(default=False)

    def __str__(self):  
        return self.title
    
class Instructor(models.Model):
    nombre = models.CharField(max_length=100)
    especialidad = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre
    


