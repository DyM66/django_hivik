from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from got.models.work_order import Ot
from got.models.failure_report import FailureReport
from got.models.routine import Ruta
from got.models.others import Task, Image
from meg.models import Megger
from got.forms import FinishOtForm, UploadImages, DocumentForm, ActForm, ActFormNoSup
from got.utils import actualizar_rutas
from mto.utils import record_execution

import uuid
import base64


TODAY = timezone.now().date()


class OtDetailView(LoginRequiredMixin, generic.DetailView):
    model = Ot
    template_name = 'got/ots/ot_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['state_form'] = FinishOtForm()
        context['image_form'] = UploadImages()
        context['doc_form'] = DocumentForm()

        if self.request.user.groups.filter(name='mto_members').exists():
            context['task_form'] = ActForm()
        else:
            context['task_form'] = ActFormNoSup()

        context['all_tasks_finished'] = not self.get_object().task_set.filter(finished=False).exists()
        context['has_activities'] = self.get_object().task_set.exists()

        failure_report = FailureReport.objects.filter(related_ot=self.get_object())
        context['failure_report'] = failure_report
        context['failure'] = failure_report.exists()

        rutas = self.get_object().ruta_set.all()
        context['rutas'] = rutas
        context['equipos'] = set([ruta.equipo for ruta in rutas])

        system = self.get_object().system
        context['electric_motors'] = system.equipos.filter(Q(type__code='e') | Q(type__code='g'))
        context['has_electric_motors'] = system.equipos.filter(Q(type__code='e') | Q(type__code='g')).exists()
        context['megger_tests'] = Megger.objects.filter(ot=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        ot = self.get_object()
        
        if 'add-doc' in request.POST:
            doc_form = DocumentForm(request.POST, request.FILES, ot=ot)
            if doc_form.is_valid():
                doc_form.save()
                return redirect(ot.get_absolute_url()) 
            else:
                print(doc_form.errors)

        if 'delete_task' in request.POST:
            task_id = request.POST.get('delete_task_id')
            task = Task.objects.get(id=task_id, ot=ot)
            task.modified_by = request.user 
            task.save()
            task.delete()
            return redirect(ot.get_absolute_url()) 
    
        task_form_class = ActForm if request.user.groups.filter(name='mto_members').exists() else ActFormNoSup
        task_form = task_form_class(request.POST, request.FILES)
        image_form = UploadImages(request.POST, request.FILES)

        if task_form.is_valid() and image_form.is_valid():
            task = task_form.save(commit=False)
            task.ot = ot
            task.user = task.responsible.get_full_name()
            task.modified_by = request.user 
            task.save()

            for file in request.FILES.getlist('file_field'):
                Image.objects.create(task=task, image=file)
        
        state_form = FinishOtForm(request.POST)
        if 'finish_ot' in request.POST and state_form.is_valid():
            # Cerrar la OT
            self.object.state = 'f'
            self.object.modified_by = request.user
            signature_image = request.FILES.get('signature_image', None)
            signature_data = request.POST.get('sign_supervisor', None)

            # Guardar firma del supervisor
            if signature_image:
                self.object.sign_supervision = signature_image
            elif signature_data:
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                filename = f'supervisor_signature_{uuid.uuid4()}.{ext}'
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                self.object.sign_supervision.save(filename, data, save=True)
            
            self.object.save()

            # Actualizar rutinas de mantenimiento relacionadas y registrar ejecuciones en el PM
            rutas = Ruta.objects.filter(ot=ot)
            for ruta in rutas:
                actualizar_rutas(ruta)
                plan = ruta.maintenance_plans.filter(period_start__lte=TODAY, period_end__gte=TODAY).first()
                if plan:
                    success = record_execution(plan, TODAY)
                    if not success:
                        self.stdout.write(f"No se pudo registrar la ejecución para la ruta {ruta.name} en la fecha {TODAY}")

            # Cerrar reportes de averias relacionados
            fallas = FailureReport.objects.filter(related_ot=ot)
            for fail in fallas:
                fail.closed = True
                fail.modified_by = request.user
                fail.save()

            return redirect(ot.get_absolute_url())

        context = {'ot': ot, 'task_form': task_form, 'state_form': state_form}
        return render(request, self.template_name, context)

