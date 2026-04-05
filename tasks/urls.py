from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.shortcuts import render
from .views import list_tasks, create_task, delete_task, edit_task, update_task, api_clases
from django.urls import path
from . import views

urlpatterns=[
    path('', list_tasks, name='list_tasks'),
    path('create/', create_task, name='create_task'),
    path('delete/<int:task_id>/', delete_task, name='delete_task'),
    path('edit/<int:id>/', edit_task, name='edit_task'),        # Mostrar formulario
     path('update/<int:task_id>/', update_task, name='update_task'),
    path('calendario/', lambda request: render(request, 'calendario_full.html'), name='calendario_clases'),
    path('api/clases/', api_clases, name='clases_api'),
    path('informe/', views.informe_ultimas_fechas, name='informe_ultimas_fechas'),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)



