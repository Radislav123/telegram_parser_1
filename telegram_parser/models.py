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


# проверяемые чаты
class Channel(BaseModel):
    name = models.CharField(max_length = 255)
    telegram_id = models.IntegerField(unique = True)
    userbot = models.CharField(max_length = 255, null = True)


class Project(BaseModel):
    name = models.CharField(max_length = 255, unique = True)
    keywords = models.TextField()
    stop_words = models.TextField()
    post_channel = models.IntegerField()
