# dth/models/positions.py
from django.db import models

class Position(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Document(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class PositionDocument(models.Model):
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='position_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='document_positions')
    mandatory = models.BooleanField(default=True)

    class Meta:
        unique_together = ('position', 'document')

    def __str__(self):
        return f"{self.position.name} - {self.document.name}"

class EmployeeDocument(models.Model):
    employee = models.ForeignKey('Nomina', on_delete=models.CASCADE, related_name='employee_documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    file = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'document')

    def __str__(self):
        return f"{self.employee.name} - {self.document.name}"
