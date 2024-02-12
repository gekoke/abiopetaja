from django.contrib import admin

from app.models import File, Pset, Template, TemplateProblem

admin.site.register(Template)
admin.site.register(TemplateProblem)
admin.site.register(File)
admin.site.register(Pset)
