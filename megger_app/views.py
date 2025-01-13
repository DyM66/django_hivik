from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from got.utils import render_to_pdf
from .forms import *

def megger_view(request, pk):
    megger = get_object_or_404(Megger, pk=pk) 
    # estator_inicial_1min:
    estator_i_1 = get_object_or_404(Estator, megger=megger, test_type='i', time_type='1')
    estator_i_2 = get_object_or_404(Estator, megger=megger, test_type='i', time_type='2')
    estator_f_1 = get_object_or_404(Estator, megger=megger, test_type='f', time_type='1')
    estator_f_2 = get_object_or_404(Estator, megger=megger, test_type='f', time_type='2')

    excitatriz_i = get_object_or_404(Excitatriz, megger=megger, test_type='i')
    excitatriz_f = get_object_or_404(Excitatriz, megger=megger, test_type='f')
    rotormain = get_object_or_404(RotorMain, megger=megger)
    rotoraux = get_object_or_404(RotorAux, megger=megger)
    rodamientosescudos = get_object_or_404(RodamientosEscudos, megger=megger)

    form_estator_i_1 = EstatorForm(request.POST or None, instance=estator_i_1)
    form_estator_i_2 = EstatorForm(request.POST or None, instance=estator_i_2)
    form_estator_f_1 = EstatorForm(request.POST or None, instance=estator_f_1)
    form_estator_f_2 = EstatorForm(request.POST or None, instance=estator_f_2)

    form_excitatriz_i = ExcitatrizForm(request.POST or None, instance=excitatriz_i)
    form_excitatriz_f = ExcitatrizForm(request.POST or None, instance=excitatriz_f)

    rotormain_form = RotorMainForm(request.POST or None, instance=rotormain)
    rotoraux_form = RotorAuxForm(request.POST or None, instance=rotoraux)
    rodamientosescudos_form = RodamientosEscudosForm(request.POST or None, instance=rodamientosescudos)

    if request.method == 'POST':
        form_estator_i_1 = EstatorForm(request.POST, instance=estator_i_1)
        form_estator_i_2 = EstatorForm(request.POST, instance=estator_i_2)
        form_estator_f_1 = EstatorForm(request.POST, instance=estator_f_1)
        form_estator_f_2 = EstatorForm(request.POST, instance=estator_f_2)

        form_excitatriz_i = ExcitatrizForm(request.POST, instance=excitatriz_i)
        form_excitatriz_f = ExcitatrizForm(request.POST, instance=excitatriz_f)
        rotormain_form = RotorMainForm(request.POST, instance=rotormain)
        rotoraux_form = RotorAuxForm(request.POST, instance=rotoraux)
        rodamientosescudos_form = RodamientosEscudosForm(request.POST, instance=rodamientosescudos)

        if 'submit_estator_i_1' in request.POST:
            if form_estator_i_1.is_valid():
                form_estator_i_1.save()
                return redirect('meg:meg-detail', pk=megger.pk)
        if 'submit_estator_i_2' in request.POST:
            if form_estator_i_2.is_valid():
                form_estator_i_2.save()
                return redirect('meg:meg-detail', pk=megger.pk)
        if 'submit_estator_f_1' in request.POST:
            if form_estator_f_1.is_valid():
                form_estator_f_1.save()
                return redirect('meg:meg-detail', pk=megger.pk)
        if 'submit_estator_f_2' in request.POST:
            if form_estator_f_2.is_valid():
                form_estator_f_2.save()
                return redirect('meg:meg-detail', pk=megger.pk)
            
        if 'submit_excitatriz_i' in request.POST:
            if form_excitatriz_i.is_valid():
                form_excitatriz_i.save()
                return redirect('meg:meg-detail', pk=megger.pk)
        if 'submit_excitatriz_f' in request.POST:
            if form_excitatriz_f.is_valid():
                form_excitatriz_f.save()
                return redirect('meg:meg-detail', pk=megger.pk)
            

        elif 'submit_rotormain' in request.POST:
            if rotormain_form.is_valid():
                rotormain_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_rotoraux' in request.POST:
            if rotoraux_form.is_valid():
                rotoraux_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_rodamientosescudos' in request.POST:
            if rodamientosescudos_form.is_valid():
                rodamientosescudos_form.save()
                return redirect('got:meg-detail', pk=megger.pk)

    context = {
        'megger': megger,
        'form_estator_i_1': form_estator_i_1,
        'form_estator_i_2': form_estator_i_2,
        'form_estator_f_1': form_estator_f_1,
        'form_estator_f_2': form_estator_f_2,

        'form_excitatriz_i': form_excitatriz_i,
        'form_excitatriz_f': form_excitatriz_f,
        'rotormain_form': rotormain_form,
        'rotoraux_form': rotoraux_form,
        'rodamientosescudos_form': rodamientosescudos_form,
    }
    return render(request, 'meg/megger_form.html', context)


def create_megger(request, ot_id):
    """
    Crea un registro Megger vinculado a la OT (ot_id) y al equipo que envíen en POST.
    Crea los subregistros necesarios.
    """
    if request.method == 'POST':
        ot = get_object_or_404(Ot, num_ot=ot_id)
        equipo_id = request.POST.get('equipo')
        equipo = get_object_or_404(Equipo, code=equipo_id)

        megger = Megger.objects.create(ot=ot, equipo=equipo)

        # 2) Creamos 4 registros Estator:
        #   (i,1), (i,2), (f,1), (f,2)
        Estator.objects.create(megger=megger, test_type='i', time_type='1')
        Estator.objects.create(megger=megger, test_type='i', time_type='2')
        Estator.objects.create(megger=megger, test_type='f', time_type='1')
        Estator.objects.create(megger=megger, test_type='f', time_type='2')

        # 3) Creamos 2 registros excitatriz (inicial y final)
        Excitatriz.objects.create(megger=megger, test_type='i')
        Excitatriz.objects.create(megger=megger, test_type='f')

        RotorMain.objects.create(megger=megger, test_type='i')
        RotorAux.objects.create(megger=megger, test_type='i')
        RodamientosEscudos.objects.create(megger=megger, test_type='i')

        return redirect('meg:meg-detail', pk=megger.pk)
    


def megger_pdf(request, pk):
    # 1) Obtener el registro principal Megger
    registro = get_object_or_404(Megger, pk=pk)

    # 2) Obtener subregistros de Estator:
    #    a) Prueba Inicial (i) => con time_type='1' y time_type='2'
    #       -> i_1 y i_2
    #    b) Prueba Final (f)   => f_1 y f_2
    estator_i_1 = get_object_or_404(
        Estator, 
        megger=registro, 
        test_type='i',  # inicial
        time_type='1'   # 1 min
    )
    estator_i_2 = get_object_or_404(
        Estator, 
        megger=registro, 
        test_type='i',
        time_type='2'   # 10 min (o como lo manejes)
    )
    estator_f_1 = get_object_or_404(
        Estator, 
        megger=registro, 
        test_type='f',  
        time_type='1'
    )
    estator_f_2 = get_object_or_404(
        Estator, 
        megger=registro, 
        test_type='f',
        time_type='2'
    )

    # 3) Obtener subregistros de Excitatriz (inicial y final)
    excitatriz_i = get_object_or_404(
        Excitatriz,
        megger=registro,
        test_type='i'
    )
    excitatriz_f = get_object_or_404(
        Excitatriz,
        megger=registro,
        test_type='f'
    )

    # 4) Obtener RotorMain, RotorAux, RodamientosEscudos
    #    Dependiendo de cómo lo manejas, si solo existe 1 por Megger, 
    #    se haría un simple get_object_or_404. 
    rotormain   = get_object_or_404(RotorMain,   megger=registro)
    rotoraux    = get_object_or_404(RotorAux,    megger=registro)
    rodamientos = get_object_or_404(RodamientosEscudos, megger=registro)

    # 5) Construir el contexto para la plantilla
    context = {
        'meg': registro,       # El Megger en sí
        # Cuatro instancias de Estator:
        'estator_i_1': estator_i_1,
        'estator_i_2': estator_i_2,
        'estator_f_1': estator_f_1,
        'estator_f_2': estator_f_2,
        # Dos de Excitatriz:
        'excitatriz_i': excitatriz_i,
        'excitatriz_f': excitatriz_f,
        # Rotor & Rodamientos:
        'rotormain':   rotormain,
        'rotoraux':    rotoraux,
        'rodamientosescudos': rodamientos,
    }

    # 6) Renderizar a PDF (o un HttpResponse con PDF)
    return render_to_pdf('meg/meg_detail.html', context)
