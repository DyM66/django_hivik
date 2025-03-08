# tic/views.py
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from .models import Ticket
from .forms import TicketForm
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect

class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tic/ticket_create.html'
    success_url = reverse_lazy('tic:ticket-list')
    
    def form_valid(self, form):
        form.instance.reporter = self.request.user
        self.object = form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True, 
                'message': 'Su solicitud ha sido enviada con éxito y será revisada pronto por el departamento de Tecnologías.'
            })
        else:
            return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        else:
            return super().form_invalid(form)

class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tic/ticket_list.html'
    context_object_name = 'tickets'
    
    def get_queryset(self):
        # Los administradores ven todos los tickets, el resto solo los suyos
        if self.request.user.groups.filter(name='tic_members').exists():
            return Ticket.objects.all().order_by('-created_at')
        return Ticket.objects.filter(reporter=self.request.user).order_by('-created_at')

class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tic/ticket_detail.html'
    context_object_name = 'ticket'


@login_required
def take_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # Solo permite tomar el ticket si está abierto y el usuario pertenece a tic_members
    if ticket.state != 'abierto' or ticket.taken_by:
        return HttpResponseForbidden("No se puede tomar este ticket.")
    if not request.user.groups.filter(name='tic_members').exists():
        return HttpResponseForbidden("No tienes permisos para tomar este ticket.")
    ticket.taken_by = request.user
    ticket.state = 'en_proceso'
    ticket.save()
    return redirect('tic:ticket-detail', pk=ticket.pk)


@login_required
def close_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    # Solo el usuario asignado puede cerrar o actualizar el ticket
    if ticket.taken_by != request.user:
        return HttpResponseForbidden("No tienes permiso para cerrar este ticket.")
    
    if request.method == "POST":
        solution = request.POST.get('solution')
        action = request.POST.get('action')
        if solution:
            ticket.solution = solution
            if action == "close":
                ticket.state = 'cerrado'
            # Si action es "save", solo se guarda la solución sin cambiar el estado
            ticket.save()
        return redirect('tic:ticket-detail', pk=ticket.pk)
    
    return redirect('tic:ticket-detail', pk=ticket.pk)


class TicketUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Ticket
    fields = ['state', 'solution']
    template_name = 'tic/ticket_update.html'
    success_url = reverse_lazy('tic:ticket-list')
    
    def test_func(self):
        # Solo los administradores pueden actualizar el ticket
        return self.request.user.groups.filter(name='administradores').exists()


class TicketDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Ticket
    template_name = 'tic/ticket_confirm_delete.html'
    success_url = reverse_lazy('tic:ticket-list')
    
    def test_func(self):
        # Permitir eliminar si el usuario es el reportante o pertenece al grupo "administradores"
        ticket = self.get_object()
        return ticket.reporter == self.request.user or self.request.user.groups.filter(name='administradores').exists()