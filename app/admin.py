from django.contrib import admin

from app.models import Template, TemplateProblem, Test

admin.site.register(Template)
admin.site.register(TemplateProblem)
admin.site.register(Test)
