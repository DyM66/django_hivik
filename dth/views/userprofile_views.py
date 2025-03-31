from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse

from dth.models.payroll import UserProfile
from dth.forms import UserProfileForm

@login_required
def profile_update(request):
    user = request.user
    # Intenta obtener el perfil; si no existe, créalo
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            # Actualizar datos del usuario
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            user.save()
            # Guardar perfil
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('got:asset-list')
        else:
            messages.error(request, 'Por favor corrige los errores indicados.')
    else:
        form = UserProfileForm(instance=profile, user=user, initial={'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email,})
    return render(request, 'dth/profile_update.html', {'form': form})


@login_required
@require_POST
def toggle_view_mode(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    new_mode = request.POST.get('mode')
    if new_mode in ['c', 't']:
        profile.payroll_view_mode = new_mode
        profile.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)
