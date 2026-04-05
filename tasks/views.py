from django.shortcuts import render, redirect, get_object_or_404
from .models import Task
from datetime import time, timedelta, datetime
from django.contrib import messages
from .models import Task, Instructor
from django.http import JsonResponse
from django.db.models import Q
from django.db.models import Max

def list_tasks(request):
    tasks = Task.objects.all().order_by('-id')
    instructores = Instructor.objects.all()
    return render(request, 'list_tasks.html', {
        'tasks': tasks,
        'instructores': instructores
    })

def create_task(request):
    instructores = Instructor.objects.all()

    if request.method == 'POST':
        form_data = request.POST
        instructor_id = form_data.get('instructor')
        fecha_inicio = form_data.get('fecha_inicio')
        fecha_fin = form_data.get('fecha_fin')
        hora = form_data.get('hora')

        # Obtener el nombre del instructor
        instructor_nombre = Instructor.objects.get(id=instructor_id).nombre

        # Buscar tarea en conflicto
        conflict_task = Task.objects.filter(
            instructor=instructor_nombre,  # ✅ ahora compara texto con texto
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio,
            hora=hora
        ).first()

        if conflict_task:
            return render(request, 'create_task.html', {
                'instructores': instructores,
                'form_data': form_data,
                'conflict_task': conflict_task
            })

        # Crear la tarea con el nombre del instructor (no el objeto)
        Task.objects.create(
            instructor=instructor_nombre,  # ✅ se guarda texto
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora=hora,
            title=form_data.get('title'),
            description=form_data.get('description'),
        )
        return redirect('list_tasks')

    return render(request, 'create_task.html', {'instructores': instructores})

def delete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.delete()
    return redirect('list_tasks')

def edit_task(request, id):
    task = get_object_or_404(Task, pk=id)
    instructores = Instructor.objects.all()
    return render(request, 'edit_task.html', {
        'task': task,
        'instructores': instructores
    })

def update_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == 'POST':
        form_data = request.POST
        title = form_data.get('title')
        description = form_data.get('description')
        fecha_inicio = form_data.get('fecha_inicio')
        fecha_fin = form_data.get('fecha_fin')
        hora = form_data.get('hora')
        instructor_id = form_data.get('instructor')

        instructor = Instructor.objects.get(id=instructor_id)
        instructor_nombre = instructor.nombre

        # Buscar conflicto (excluyendo la tarea actual)
        conflict_task = Task.objects.filter(
            instructor=instructor_nombre,
            fecha_inicio__lte=fecha_fin,
            fecha_fin__gte=fecha_inicio,
            hora=hora
        ).exclude(id=task.id).first()

        if conflict_task:
            instructores = Instructor.objects.all()
            return render(request, 'edit_task.html', {
                'task': task,
                'instructores': instructores,
                'conflict_task': conflict_task,
                'form_data': form_data
            })

        # Si no hay conflicto, actualizar
        task.title = title
        task.description = description
        task.fecha_inicio = fecha_inicio
        task.fecha_fin = fecha_fin
        task.hora = hora
        task.instructor = instructor_nombre
        task.save()

        messages.success(request, "Tarea actualizada exitosamente.")
        return redirect('list_tasks')

    instructores = Instructor.objects.all()
    return render(request, 'edit_task.html', {
        'task': task,
        'instructores': instructores
    })

def api_clases(request):
    tareas = (
        Task.objects
        .values('instructor', 'hora', 'fecha_fin')
        .order_by('instructor', 'hora')
    )

    eventos = []
    for tarea in tareas:
        fecha_ajustada = ajustar_fecha(tarea['fecha_fin'])
        if fecha_ajustada:
            # Combina fecha ajustada + hora (asumiendo que hora es tipo time)
            fecha_hora = datetime.combine(fecha_ajustada, tarea['hora'])
            eventos.append({
                'title': f"{tarea['instructor']}",
                'start': fecha_hora.isoformat(),
                'allDay': False,  # importante para mostrar hora
            })

    return JsonResponse(eventos, safe=False)


def ajustar_fecha(fecha):
    dia_original = fecha.weekday()  # lunes=0, ..., domingo=6

    if dia_original == 4:  # viernes
        # mover directamente al lunes siguiente
        return fecha + timedelta(days=3)
    elif dia_original == 5:  # sábado
        # mover al sábado siguiente
        return fecha + timedelta(days=7)
    else:
        # cualquier otro día: sumar 1 día
        return fecha + timedelta(days=1)

def informe_ultimas_fechas(request):
    resultados = (
        Task.objects
        .values('instructor', 'hora')
        .annotate(ultima_fecha=Max('fecha_fin'))
        .order_by('instructor', 'hora')
    )

    # Ajustar fechas
    resultados_ajustados = []
    for r in resultados:
        fecha_original = r['ultima_fecha']
        if fecha_original:
            r['fecha_ajustada'] = ajustar_fecha(fecha_original)
        else:
            r['fecha_ajustada'] = None
        resultados_ajustados.append(r)

    return render(request, 'tasks/informe_ultimas_fechas.html', {'resultados': resultados_ajustados})
