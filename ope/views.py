from django.shortcuts import render
from .models import *



'OPERATIONS VIEW'
def OperationListView(request):
    assets = Asset.objects.filter(area='a', show=True)

    today = timezone.now().date()
    show_past = request.GET.get('show_past', 'false').lower() == 'true'
    if show_past:
        operaciones_list = Operation.objects.order_by('start').prefetch_related(
            Prefetch(
                'requirement_set',
                queryset=Requirement.objects.order_by('responsable').prefetch_related('images')
            )
        )
    else:
        operaciones_list = Operation.objects.filter(end__gte=today).order_by('start').prefetch_related(
            Prefetch(
                'requirement_set',
                queryset=Requirement.objects.order_by('responsable').prefetch_related('images')
            )
        )

    # Paginación
    page = request.GET.get('page', 1)
    paginator = Paginator(operaciones_list, 40)  # Mostrar 10 operaciones por página

    try:
        operaciones = paginator.page(page)
    except PageNotAnInteger:
        operaciones = paginator.page(1)
    except EmptyPage:
        operaciones = paginator.page(paginator.num_pages)

    # Datos para el gráfico: incluir todas las operaciones
    operations_data = []
    for asset in assets:
        asset_operations = asset.operation_set.all().values(
            'start', 'end', 'proyecto', 'requirements', 'confirmado'
        )
        operations_data.append({
            'asset': asset,
            'operations': list(asset_operations)
        })

    form = OperationForm(request.POST or None)
    modal_open = False 

    if request.method == 'POST':
        form = OperationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path)
        else:
            modal_open = True 
    else:
        form = OperationForm()

    context = {
        'operations_data': operations_data,
        'operation_form': form,
        'modal_open': modal_open,
        'operaciones': operaciones,
        'requirement_form': RequirementForm(),
        'upload_images_form': UploadImages(),
        'show_past': show_past,
    }

    return render(request, 'got/operations/operation_list.html', context)


class OperationUpdate(UpdateView):
    model = Operation
    form_class = OperationForm
    template_name = 'got/operations/operation_form.html'

    def get_success_url(self):
        return reverse('got:operation-list')


class OperationDelete(DeleteView):
    model = Operation
    success_url = reverse_lazy('got:operation-list')
    template_name = 'got/operations/operation_confirm_delete.html'



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
            for f in request.FILES.getlist('file_field'):
                Image.objects.create(image=f, requirements=requirement)
            return redirect('got:operation-list')
    else:
        requirement_form = RequirementForm()
        upload_images_form = UploadImages()
    context = {
        'requirement_form': requirement_form,
        'upload_images_form': upload_images_form,
        'operation': operation,
    }
    return render(request, 'got/operations/requirement_form.html', context)


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
            if can_delete_images:
                images_to_delete = request.POST.getlist('delete_images')
                Image.objects.filter(id__in=images_to_delete).delete()
            # Guardar nuevas imágenes
            for f in request.FILES.getlist('file_field'):
                Image.objects.create(image=f, requirements=requirement)
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
    return render(request, 'got/operations/requirement_form.html', context)


def requirement_delete(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    if request.method == 'POST':
        requirement.delete()
        return redirect('got:operation-list')
    return render(request, 'got/operations/requirement_confirm_delete.html', {'requirement': requirement})


