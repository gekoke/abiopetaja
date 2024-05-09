from django.contrib import admin

from app.models import Template, TemplateProblem, Test, UserFeedback


class EntityAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at")


def register_entity(entity):
    admin.site.register(entity, EntityAdmin)


register_entity(Template)
register_entity(TemplateProblem)
register_entity(Test)
register_entity(UserFeedback)
