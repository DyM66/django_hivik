from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse

from got.models.system import System
from got.paths import get_upload_path

class Ot(models.Model):
    STATUS = (('a', 'Abierto'), ('x', 'En ejecución'), ('f', 'Finalizado'), ('c', 'Cancelado'),)
    TIPO_MTTO = (('p', 'Preventivo'), ('c', 'Correctivo'), ('m', 'Modificativo'),)
    creation_date = models.DateField(auto_now_add=True)
    num_ot = models.AutoField(primary_key=True)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    description = models.TextField()
    supervisor = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(choices=STATUS, default='x', max_length=1)
    tipo_mtto = models.CharField(choices=TIPO_MTTO, max_length=1)
    sign_supervision = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_ots')

    closing_date = models.DateField(null=True, blank=True)

    def all_tasks_finished(self):
        related_tasks = self.task_set.all()
        if all(task.finished for task in related_tasks):
            return True
        return False

    def __str__(self):
        return '%s - %s' % (self.num_ot, self.description)

    def get_absolute_url(self):
        return reverse('got:ot-detail', args=[str(self.num_ot)])
    
    def save(self, *args, **kwargs):
        # Si ya existe la OT, obtenemos la instancia anterior
        if self.pk:
            old = Ot.objects.get(pk=self.pk)
            # Si el estado pasa de algo distinto a 'f' a 'f' y no se ha registrado la fecha de cierre
            if old.state != 'f' and self.state == 'f' and not self.closing_date:
                self.closing_date = timezone.now().date()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-num_ot']