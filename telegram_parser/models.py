from django.db import models

import logger
from .settings import Settings


class BaseModel(models.Model):
    class Meta:
        abstract = True

    settings = Settings()
    logger = logger.Logger(Meta.__qualname__[:-5])

    def __str__(self) -> str:
        if hasattr(self, "name"):
            string = self.name
        else:
            string = super().__str__()
        return string

    @classmethod
    def get_field_verbose_name(cls, field_name: str) -> str:
        return cls._meta.get_field(field_name).verbose_name


class Userbot(BaseModel):
    name = models.CharField(max_length = 255, null = True)
    phone = models.CharField(max_length = 50, unique = True)
    last_channel_join_date = models.DateField(auto_now = True)
    day_channels_join_counter = models.IntegerField(default = 0)
    cloud_password = models.CharField(max_length = 100, blank = True)
    verification_code = models.CharField(max_length = 100, null = True)


# проверяемые чаты
class Channel(BaseModel):
    name = models.CharField(max_length = 255, null = True)
    link = models.CharField(max_length = 255)
    telegram_id = models.IntegerField(null = True)


class Project(BaseModel):
    name = models.CharField(max_length = 255, unique = True)
    keywords = models.TextField(blank = True)
    stop_words = models.TextField(blank = True)
    post_channel_link = models.CharField(max_length = 255)
    post_channel_telegram_id = models.IntegerField(null = True)


# сопоставление ботов и каналов, на которые бот подписан
class UserbotChannel(BaseModel):
    userbot = models.ForeignKey(Userbot, models.RESTRICT)
    channel = models.ForeignKey(Channel, models.RESTRICT)


class UserbotProject(BaseModel):
    userbot = models.ForeignKey(Userbot, models.RESTRICT)
    project = models.ForeignKey(Project, models.RESTRICT)
