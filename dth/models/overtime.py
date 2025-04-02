# dth/models/overtime.py

from django.db import models
from django.contrib.auth.models import User
from .payroll import Nomina
from dth.utils import is_sunday_or_holiday, diff_in_hours, overlap_in_hours, DAY_START, NIGHT_START
from datetime import time


class OvertimeProject(models.Model):
    description = models.TextField()
    asset = models.ForeignKey(
        'got.Asset',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    reported_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    report_date = models.DateField(null=True, blank=True)
    ot = models.ForeignKey(
        'got.Ot',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


class Overtime(models.Model):
    STATE = (('a', 'Aprobado'), ('b', 'No aprobado'), ('c', 'Pendiente'))
    start = models.TimeField()
    end = models.TimeField()
    worker = models.ForeignKey(
        Nomina,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    state = models.CharField(max_length=1, choices=STATE, default='c')
    project = models.ForeignKey(
        OvertimeProject,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    remarks = models.TextField(null=True, blank=True)

    # OBSOLETO
    nombre_completo = models.CharField(
        max_length=200, default='',
        null=True,
        blank=True
    )
    cedula = models.CharField(max_length=20, default='', null=True, blank=True)
    cargo = models.CharField(
        max_length=1,
        choices=(
            ('a', 'Capitán'),
            ('b', 'Primer Oficial de Puente'),
            ('c', 'Marino'),
            ('d', 'Jefe de Máquinas'),
            ('e', 'Primer Oficial de Máquinas'),
            ('f', 'Maquinista'),
            ('g', 'Otro'),
        ),
        null=True,
        blank=True
    )

    @property
    def total_hours_festive(self):
        if not self.project or not self.project.report_date:
            return 0.0
        if is_sunday_or_holiday(self.project.report_date):
            return diff_in_hours(self.start, self.end)
        return 0.0

    @property
    def total_hours_ordinary(self):
        if not self.project or not self.project.report_date:
            return 0.0
        if is_sunday_or_holiday(self.project.report_date):
            return 0.0
        # Calcular las horas de solapamiento con [06:00, 21:00)
        ordinary_hours = overlap_in_hours(
            self.start, self.end, DAY_START, NIGHT_START
        )
        return ordinary_hours

    @property
    def total_hours_night(self):
        if not self.project or not self.project.report_date:
            return 0.0
        if is_sunday_or_holiday(self.project.report_date):
            return 0.0
        part1 = overlap_in_hours(
            self.start, self.end, NIGHT_START, time(23, 59, 59)
            )
        part2 = overlap_in_hours(self.start, self.end, time(0, 0), DAY_START)
        return part1 + part2

    def __str__(self):
        return f"{self.nombre_completo} - {self.get_cargo_display()}"

    class Meta:
        db_table = 'got_overtime'
        permissions = [('can_approve_overtime', 'Puede aprobar horas extras'),]
