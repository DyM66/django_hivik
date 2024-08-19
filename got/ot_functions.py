from django.template.loader import get_template
from django.utils import timezone
from io import BytesIO
from xhtml2pdf import pisa

def actualizar_rutas_dependientes(ruta):
    ruta.intervention_date = timezone.now()
    ruta.save()
    if ruta.dependencia is not None:
        actualizar_rutas_dependientes(ruta.dependencia)


def generate_pdf_content(ot):

    template_path = 'got/pdf_template.html'
    context = {'ot': ot}
    template = get_template(template_path)
    html = template.render(context)
    pdf_content = BytesIO()

    pisa.CreatePDF(html, dest=pdf_content)

    return pdf_content.getvalue()