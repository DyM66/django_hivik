# inventory_management/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import generic

from got.models import Item
from got.forms import ItemForm


'EXPERIMENTAL VIEWS'
class ItemManagementView(generic.TemplateView):
    template_name = 'inventory_management/item_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = Item.objects.all()
        context['form'] = ItemForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.modified_by = request.user
            form.save()
            return redirect(reverse('inv:item_management'))

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect(reverse('inv:item_management'))
    else:
        form = ItemForm(instance=item)

    return render(request, 'got/solicitud/edit_item.html', {'form': form, 'item': item})


