from django.db import models
from got.models import Asset


class Operation(models.Model):
    start = models.DateField()
    end = models.DateField()
    proyecto = models.CharField(max_length=100)
    requirements = models.TextField(null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    confirmado = models.BooleanField(default=False)

    def requirements_progress(self):
        total_requirements = self.requirement_set.count()
        if total_requirements == 0:
            return None
        approved_requirements = self.requirement_set.filter(approved=True).count()
        progress_percentage = (approved_requirements / total_requirements) * 100
        return int(progress_percentage)

    def __str__(self):
        return f"{self.proyecto}/{self.asset} ({self.start} - {self.start})"
    
    class Meta:
        db_table = 'got_operation'


# Model 12: Requerimientos para proyectos
class Requirement(models.Model):
    operation = models.ForeignKey(Operation, on_delete=models.CASCADE)
    text = models.TextField()
    approved = models.BooleanField(default=False)
    novedad = models.TextField(null=True, blank=True)
    responsable = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        permissions = [('can_create_requirement', 'Can create requirement'), ('can_delete_requirement', 'Can delete requirement'),]
        db_table = 'got_requirement'