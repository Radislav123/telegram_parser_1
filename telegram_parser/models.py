import datetime

from django.db import models

import logger
from .settings import Settings


def get_username_from_link(link: str) -> str:
    if link.startswith("http"):
        parts = link.split('/')
        username = parts[-1]
        if username.startswith('+'):
            username = link
        elif len(parts) > 1 and parts[-2] == "joinchat":
            username = link
    else:
        username = link
    return username


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
    last_channel_join_date = models.DateField()
    day_channels_join_counter = models.IntegerField(default = 0)
    cloud_password = models.CharField(max_length = 100, blank = True)
    verification_code = models.CharField(max_length = 100, null = True)
    active = models.BooleanField(null = True)

    def save(self, *args, **kwargs) -> None:
        if self.last_channel_join_date is None:
            self.last_channel_join_date = datetime.datetime.today()
        super().save(*args, **kwargs)

    # noinspection SpellCheckingInspection
    async def asave(self, *args, **kwargs) -> None:
        if self.last_channel_join_date is None:
            self.last_channel_join_date = datetime.datetime.today()
        await super().asave(*args, **kwargs)

    def update_join_date(self) -> None:
        self.last_channel_join_date = datetime.datetime.today()


# проверяемые чаты
class Channel(BaseModel):
    name = models.CharField(max_length = 255, null = True)
    link = models.CharField(max_length = 255)
    telegram_id = models.IntegerField(null = True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._username: str | None = None

    @property
    def username(self) -> str:
        if self._username is None:
            self._username = get_username_from_link(self.link)
        return self._username


class Project(BaseModel):
    name = models.CharField(max_length = 255, unique = True)
    keywords = models.TextField(blank = True)
    stop_words = models.TextField(blank = True)
    post_channel_link = models.CharField(max_length = 255)
    post_channel_telegram_id = models.IntegerField(null = True)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._post_channel_username: str | None = None

    @property
    def post_channel_username(self) -> str:
        if self._post_channel_username is None:
            self._post_channel_username = get_username_from_link(self.post_channel_link)
        return self._post_channel_username


# сопоставление ботов и каналов, на которые бот подписан
class UserbotChannel(BaseModel):
    userbot = models.ForeignKey(Userbot, models.CASCADE)
    channel = models.ForeignKey(Channel, models.CASCADE)


class UserbotProject(BaseModel):
    userbot = models.ForeignKey(Userbot, models.CASCADE)
    project = models.ForeignKey(Project, models.CASCADE)
