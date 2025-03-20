from django.shortcuts import render
from django.utils import timezone
from django.db.models import Prefetch
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse

from .models import *
from .forms import OperationForm, RequirementForm, FullRequirementForm, LimitedRequirementForm
from got.forms import UploadImages


class OperationListView(TemplateView):
    template_name = 'operations/operation_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assets = Asset.objects.filter(area='a', show=True)

        today = timezone.now().date()
        show_past = self.request.GET.get('show_past', 'false').lower() == 'true'
        if show_past:
            operaciones_list = Operation.objects.order_by('start').prefetch_related(
                Prefetch(
                    'requirement_set',
                    queryset=Requirement.objects.order_by('responsable')
                )
            )
        else:
            operaciones_list = Operation.objects.filter(end__gte=today).order_by('start').prefetch_related(
                Prefetch(
                    'requirement_set',
                    queryset=Requirement.objects.order_by('responsable')
                )
            )

        # Paginación
        page = self.request.GET.get('page', 1)
        paginator = Paginator(operaciones_list, 40)

        try:
            operaciones = paginator.page(page)
        except PageNotAnInteger:
            operaciones = paginator.page(1)
        except EmptyPage:
            operaciones = paginator.page(paginator.num_pages)

        operations_data = []
        for asset in assets:
            asset_operations = asset.operation_set.all().values(
                'id', 'start', 'end', 'proyecto', 'requirements', 'confirmado', 'asset'
            )

            operations_data.append({
                'asset': asset,
                'operations': list(asset_operations)
            })

        # 4) Si en self.kwargs o context hay un form con errores del post, lo usamos;
        #    de lo contrario creamos uno vacío
        operation_form = kwargs.get('operation_form') or OperationForm()

        context['operations_data'] = operations_data
        context['operation_form'] = operation_form
        context['modal_open'] = kwargs.get('modal_open', False)
        context['operaciones'] = operaciones
        context['requirement_form'] = RequirementForm()
        context['show_past'] = show_past
        context['assets'] = Asset.objects.filter(area='a', show=True)
        return context

    def post(self, request, *args, **kwargs):
        """
        Maneja la creación de una operación cuando se hace post.
        """
        # Verificamos si el POST viene con el name 'create_operation'
        # o un <input type="hidden" name="create_operation" ...> en el modal
        if 'create_operation' in request.POST:
            form = OperationForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect(request.path)  # Redirige a la misma vista
            else:
                # Si no es válido, re-renderizamos con errores:
                #   - le pasamos el form con errores
                #   - le pasamos modal_open=True para que abra el modal
                return self.render_to_response(
                    self.get_context_data(operation_form=form, modal_open=True)
                )

        # Si no es un POST de creación, llamamos a super:
        return super().post(request, *args, **kwargs)


@require_POST  # Asegura que sólo responda a POST
def update_operation(request, pk):
    """
    Recibe los datos de un OperationForm vía POST,
    y actualiza la operación con id=pk, retorna JSON con éxito o error.
    """
    operation = get_object_or_404(Operation, pk=pk)
    form = OperationForm(request.POST, instance=operation)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True})
    else: # Retornar errores de formulario en JSON
        print("DEBUG form errors:", form.errors)
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


class OperationDelete(DeleteView):
    model = Operation
    success_url = reverse_lazy('ope:operation-list')

    def get(self, request, *args, **kwargs):
        # Redirige si intentan GET
        return redirect('ope:operation-list')



@permission_required('got.can_create_requirement', raise_exception=True)
def requirement_create(request, operation_id):
    operation = get_object_or_404(Operation, id=operation_id)
    if request.method == 'POST':
        requirement_form = RequirementForm(request.POST)
        upload_images_form = UploadImages(request.POST, request.FILES)
        if requirement_form.is_valid() and upload_images_form.is_valid():
            requirement = requirement_form.save(commit=False)
            requirement.operation = operation
            requirement.save()
            # Acceder directamente a los archivos desde request.FILES
            # for f in request.FILES.getlist('file_field'):
                # Image.objects.create(image=f, requirements=requirement)
            return redirect('ope:operation-list')
    else:
        requirement_form = RequirementForm()
        upload_images_form = UploadImages()
    context = {
        'requirement_form': requirement_form,
        'upload_images_form': upload_images_form,
        'operation': operation,
    }
    return render(request, 'operations/requirement_form.html', context)


def requirement_update(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    if request.user.has_perm('got.can_create_requirement'):
        RequirementFormClass = FullRequirementForm
        can_delete_images = True
    else:
        RequirementFormClass = LimitedRequirementForm
        can_delete_images = False

    if request.method == 'POST':
        requirement_form = RequirementFormClass(request.POST, instance=requirement)
        upload_images_form = UploadImages(request.POST, request.FILES)
        if requirement_form.is_valid() and upload_images_form.is_valid():
            requirement_form.save()
            # Manejar eliminación de imágenes
            # if can_delete_images:
                # images_to_delete = request.POST.getlist('delete_images')
                # Image.objects.filter(id__in=images_to_delete).delete()
            # Guardar nuevas imágenes
            # for f in request.FILES.getlist('file_field'):
                # Image.objects.create(image=f, requirements=requirement)
            return redirect('got:operation-list')
    else:
        requirement_form = RequirementFormClass(instance=requirement)
        upload_images_form = UploadImages()
    context = {
        'requirement_form': requirement_form,
        'upload_images_form': upload_images_form,
        'requirement': requirement,
        'can_delete_images': can_delete_images,
    }
    return render(request, 'operations/requirement_form.html', context)


def requirement_delete(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    if request.method == 'POST':
        requirement.delete()
        return redirect('ope:operation-list')
    return render(request, 'operations/requirement_confirm_delete.html', {'requirement': requirement})


