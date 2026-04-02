from django.contrib import admin
from .models import (
    WorkObject,
    Camera,
    ViolationType,
    MedicalCheck,
    SickLeave,
    Sanction,
)

admin.site.register(WorkObject)
admin.site.register(Camera)
admin.site.register(ViolationType)
admin.site.register(MedicalCheck)
admin.site.register(SickLeave)
admin.site.register(Sanction)