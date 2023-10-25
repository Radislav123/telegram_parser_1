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


class UserBot(BaseModel):
    pass


# проверяемые чаты
class Channel(BaseModel):
    telegram_id = models.IntegerField()


class Project(BaseModel):
    name = models.CharField(max_length = 256)
    keywords = models.TextField()
    stop_words = models.TextField()
    post_channel = models.IntegerField()
