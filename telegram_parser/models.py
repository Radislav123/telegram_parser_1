from django.db import models

import logger
from .settings import Settings


class BaseModel(models.Model):
    class Meta:
        abstract = True

    settings = Settings()
    logger = logger.Logger(Meta.__qualname__[:-5])

    @classmethod
    def get_field_verbose_name(cls, field_name: str) -> str:
        return cls._meta.get_field(field_name).verbose_name


class Userbot(BaseModel):
    name = models.CharField(max_length = 255, null = True)
    phone = models.CharField(max_length = 50, unique = True)
    last_channel_join_date = models.DateField(auto_now = True)
    day_channels_join_counter = models.IntegerField(default = 0)


# проверяемые чаты
class Channel(BaseModel):
    name = models.CharField(max_length = 255, null = True)
    telegram_id = models.IntegerField(unique = True)
    userbot = models.ForeignKey(Userbot, on_delete = models.RESTRICT, null = True)


class Project(BaseModel):
    name = models.CharField(max_length = 255, unique = True)
    keywords = models.TextField(blank = True)
    stop_words = models.TextField(blank = True)
    post_channel = models.IntegerField()
