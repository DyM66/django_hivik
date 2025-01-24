from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from .models import *
from .forms import *
from django.views import generic, View
from got.models import Item, Image
from got.forms import UploadImages
from django.core.files.base import ContentFile
import base64
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.http import HttpResponse, HttpResponseRedirect
from got.utils import render_to_pdf
from django.urls import reverse_lazy
from django.contrib import messages

class OutboundListView(LoginRequiredMixin, generic.ListView):
    model = OutboundDelivery
    paginate_by = 20
    template_name = 'outbound/salidas_list.html'
    context_object_name = 'salida_list'

    def get_queryset(self):
        queryset = super().get_queryset()
        destino = self.request.GET.get('destino', '').strip()
        fecha = self.request.GET.get('fecha', '').strip()
        motivo = self.request.GET.get('motivo', '').strip()
        propietario = self.request.GET.get('propietario', '').strip()
        adicional = self.request.GET.get('adicional', '').strip()

        if destino:
            queryset = queryset.filter(destino__icontains=destino)
        if fecha:
            queryset = queryset.filter(fecha=fecha)  # Fecha en formato 'YYYY-MM-DD'
        if motivo:
            queryset = queryset.filter(motivo__icontains=motivo)
        if propietario:
            queryset = queryset.filter(propietario__icontains=propietario)
        if adicional:
            queryset = queryset.filter(adicional__icontains=adicional)
        return queryset


class SalidaCreateView(LoginRequiredMixin, View):
    form_class = SalidaForm
    template_name = 'outbound/create-salida.html'

    def get(self, request):
        items = Item.objects.all()
        form = self.form_class()
        image_form = UploadImages(request.POST, request.FILES)

        return render(request, self.template_name, {
            'items': items,
            'form': form,
            'image_form': image_form
        })

    def post(self, request):

            form = self.form_class(request.POST, request.FILES)
            image_form = UploadImages(request.POST, request.FILES)
            items_ids = request.POST.getlist('item_id[]') 
            cantidades = request.POST.getlist('cantidad[]')

            context = {
                'items': Item.objects.all(),
                'form': form,
                'image_form': image_form
            }

            if form.is_valid() and image_form.is_valid():
                solicitud = form.save(commit=False)
                solicitud.responsable = self.request.user.get_full_name()
                solicitud.save()

                # for item_id, cantidad in zip(items_ids, cantidades):
                #     if item_id and cantidad:
                #         item = get_object_or_404(Item, id=item_id)
                #         Suministro.objects.create(
                #             item=item,
                #             cantidad=int(cantidad),
                #             salida=solicitud
                #         )
                
                for file in request.FILES.getlist('file_field'):
                    Image.objects.create(salida=solicitud, image=file)
                return redirect('outbound:outbound-list')
            return render(request, self.template_name, context)


class NotifySalidaView(LoginRequiredMixin, View):

    def post(self, request, pk):
        salida = get_object_or_404(OutboundDelivery, pk=pk)
        
        # Obtener y guardar la firma
        signature_data = request.POST.get('signature')
        if signature_data:
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'signature_{uuid.uuid4()}.{ext}'
            signature_file = ContentFile(base64.b64decode(imgstr), name=filename)
            salida.sign_recibe.save(filename, signature_file, save=True)

        # Enviar el correo electrónico con el PDF adjunto
        # pdf_buffer = salida_email_pdf(salida.pk)
        # subject = f'Solicitud salida de materiales: {salida}'
        # message = f'''
        # Cordial saludo,

        # Notificación de salida.

        # Por favor, revise el archivo adjunto para más detalles.
        # '''
        # email = EmailMessage(
        #     subject,
        #     message,
        #     settings.EMAIL_HOST_USER,
        #     ['analistamto@serport.co']  # Puedes añadir más destinatarios aquí
        # )
        # email.attach(f'Salida_{salida.pk}.pdf', pdf_buffer, 'application/pdf')
        # email.send()

        # Redirigir al usuario a la página anterior
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def salida_pdf(request, pk):
    salida = OutboundDelivery.objects.get(pk=pk)
    nombre_completo = salida.responsable.split()
    if len(nombre_completo) > 1:
        first_name = nombre_completo[0]
        last_name = nombre_completo[1]
    else:
        first_name = salida.responsable
        last_name = ""

    # Buscar el usuario basado en el nombre y apellido
    try:
        user = User.objects.get(first_name=first_name, last_name=last_name)
        cargo = user.profile.cargo  # Asume que el perfil tiene un campo 'cargo'
    except User.DoesNotExist:
        cargo = 'Cargo no encontrado'
    context = {
        'rq': salida,
        'pro': cargo
        }
    return render_to_pdf('got/salidas/salida_detail.html', context)

        
class ApproveSalidaView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        solicitud = OutboundDelivery.objects.get(id=kwargs['pk'])
        solicitud.auth = not solicitud.auth
        solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

class SalidaUpdateView(LoginRequiredMixin, View):
    form_class = SalidaForm
    template_name = 'got/salidas/update-salida.html'

    def get(self, request, pk):
        salida = get_object_or_404(OutboundDelivery, pk=pk)
        form = self.form_class(instance=salida)
        image_form = UploadImages()
        items = Item.objects.all()
        # suministros = salida.suministros.all()

        return render(request, self.template_name, {
            'form': form,
            'image_form': image_form,
            'items': items,
            # 'suministros': suministros,
            'salida': salida,
        })

    def post(self, request, pk):
        salida = get_object_or_404(OutboundDelivery, pk=pk)
        form = self.form_class(request.POST, request.FILES, instance=salida)
        image_form = UploadImages(request.POST, request.FILES)
        items_ids = request.POST.getlist('item_id[]') 
        cantidades = request.POST.getlist('cantidad[]')

        context = {
            'form': form,
            'image_form': image_form,
            'items': Item.objects.all(),
            # 'suministros': salida.suministros.all(),
            'salida': salida,
        }

        if form.is_valid() and image_form.is_valid():
            salida = form.save()

            # Manejo de la firma
            signature_data = request.POST.get('signature')
            if signature_data:
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                filename = f'signature_{uuid.uuid4()}.{ext}'
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                salida.sign_recibe.save(filename, data, save=True)

            # Actualizar Suministros
            # salida.suministros.all().delete()  # Eliminar suministros existentes
            # for item_id, cantidad in zip(items_ids, cantidades):
            #     if item_id and cantidad:
            #         item = get_object_or_404(Item, id=item_id)
            #         Suministro.objects.create(
            #             item=item,
            #             cantidad=int(cantidad),
            #             salida=salida
            #         )

            # Manejo de imágenes
            # for file in request.FILES.getlist('file_field'):
            #     Image.objects.create(salida=salida, image=file)

            # # Enviar correo electrónico con el PDF adjunto
            # pdf_buffer = salida_email_pdf(salida.pk)
            # subject = f'Solicitud salida de materiales: {salida}'
            # message = f'''
            # Cordial saludo,

            # Notificación de salida.

            # Por favor, revise el archivo adjunto para más detalles.
            # '''
            # email = EmailMessage(
            #     subject,
            #     message,
            #     settings.EMAIL_HOST_USER,
            #     ['seguridad@serport.co']
            # )
            # email.attach(f'Salida_{salida.pk}.pdf', pdf_buffer, 'application/pdf')
            # email.send()
            return redirect('outbound:outbound-list')
        return render(request, self.template_name, context)
    

class PlaceListView(LoginRequiredMixin, generic.ListView):
    model = Place
    template_name = 'outbound/place_list.html'
    context_object_name = 'places'

class PlaceCreateView(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    model = Place
    form_class = PlaceForm
    template_name = 'outbound/place_form.html'
    success_url = reverse_lazy('outbound:place-list')
    permission_required = 'outbound.add_place'

    def form_valid(self, form):
        messages.success(self.request, 'Lugar creado exitosamente.')
        return super().form_valid(form)

class PlaceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    model = Place
    form_class = PlaceForm
    template_name = 'outbound/place_form.html'
    success_url = reverse_lazy('outbound:place-list')
    permission_required = 'outbound.change_place'

    def form_valid(self, form):
        messages.success(self.request, 'Lugar actualizado exitosamente.')
        return super().form_valid(form)

class PlaceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView):
    model = Place
    template_name = 'outbound/place_confirm_delete.html'
    success_url = reverse_lazy('outbound:place-list')
    permission_required = 'outbound.delete_place'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Lugar eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)
