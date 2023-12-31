import sys
from typing import Type

from django.contrib import admin

from telegram_parser import models
from .settings import Settings


def is_migration() -> bool:
    return "makemigrations" in sys.argv or "migrate" in sys.argv


def register_models(model_admins: list[Type["BaseAdmin"]]) -> None:
    for model_admin in model_admins:
        admin.site.register(model_admin.model, model_admin)


class BaseAdmin(admin.ModelAdmin):
    model = models.BaseModel
    settings = Settings()
    hidden_fields = ()
    _fieldsets = ()
    # {вставляемое_поле: поле_после_которого_вставляется}
    # {field: None} - вставится последним
    extra_list_display: dict[str, str] = {}
    not_required_fields: set[str] = set()

    def __init__(self, model, admin_site):
        self.list_display = [field for field in self._list_display if field not in self.hidden_fields]
        for field, before_field in self.extra_list_display.items():
            if before_field is None:
                self.list_display.append(field)
            else:
                self.list_display.insert(self.list_display.index(before_field), field)
        self.list_display = tuple(self.list_display)
        if self.fieldsets is not None:
            self.fieldsets += self._fieldsets
        else:
            self.fieldsets = self._fieldsets

        super().__init__(model, admin_site)

    def get_form(self, request, obj = None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in self.not_required_fields:
            form.base_fields[field_name].required = False
        return form

    @property
    def _list_display(self) -> tuple:
        # noinspection PyProtectedMember
        return tuple(field.name for field in self.model._meta.fields)


class UserbotAdmin(BaseAdmin):
    model = models.Userbot
    extra_list_display = {"new_day_channels_join_counter": None}
    not_required_fields = ("last_channel_join_date", "day_channels_join_counter", "verification_code")
    hidden_fields = ("cloud_password", "verification_code", "day_channels_join_counter")

    def new_day_channels_join_counter(self, obj: model) -> str:
        return f"{obj.day_channels_join_counter}/{self.settings.MAX_DAY_CHANNEL_JOINS}"

    new_day_channels_join_counter.short_description = "day channels join counter"


class ChanelAdmin(BaseAdmin):
    model = models.Channel
    not_required_fields = ("telegram_id",)


class ProjectAdmin(BaseAdmin):
    model = models.Project
    not_required_fields = ("post_channel_telegram_id",)


class UserbotChannel(BaseAdmin):
    model = models.UserbotChannel


class UserbotProject(BaseAdmin):
    model = models.UserbotProject


model_admins_to_register = [UserbotAdmin, ChanelAdmin, ProjectAdmin, UserbotChannel, UserbotProject]
register_models(model_admins_to_register)
