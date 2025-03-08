# tic/context_processors.py
from .forms import TicketForm

def ticket_form_processor(request):
    return {'ticket_form': TicketForm()}
