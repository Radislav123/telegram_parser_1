import asyncio
import datetime
from pathlib import Path

import pyrogram.errors.exceptions
from asgiref.sync import sync_to_async

import logger
from telegram_parser import models, settings
from telegram_parser.management.commands import telegram_parser_command


class UserbotClient(pyrogram.Client):
    settings = settings.Settings()
    db_object: models.Userbot

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.logger = logger.Logger(self.__class__.__name__)
        self.channels: dict[int, models.Channel] = {}

    async def prepare(self, channels: dict[int, models.Channel]) -> None:
        self.db_object = await models.Userbot.objects.aget(phone = self.phone_number)

        await self.check_channels(channels)
        await models.Channel.objects.filter(id__in = (x.id for x in self.channels.values())).aupdate(
            userbot = self.db_object
        )

    async def check_channels(self, channels: dict[int, models.Channel]) -> None:
        if self.db_object.last_channel_join_date < datetime.date.today():
            self.db_object.day_channels_join_counter = 0

        for channel in channels.values():
            chat = await self.get_chat(channel.telegram_id)
            if chat.type != pyrogram.enums.ChatType.PRIVATE and chat.type != pyrogram.enums.ChatType.BOT:
                try:
                    await self.get_chat_member(channel.telegram_id, "me")
                    self.channels[channel.telegram_id] = channel
                except pyrogram.errors.exceptions.UserNotParticipant:
                    if self.db_object.day_channels_join_counter < self.settings.MAX_DAY_CHANNEL_JOINS:
                        self.db_object.last_channel_join_date = datetime.date.today()
                        try:
                            await self.join_chat(channel.telegram_id)
                            self.db_object.day_channels_join_counter += 1
                            self.channels[channel.telegram_id] = channel
                        except Exception as exception:
                            self.logger.exception(str(exception))
            else:
                self.channels[channel.telegram_id] = channel

        await self.db_object.asave()

    @staticmethod
    async def track(self: "UserbotClient", message: pyrogram.types.Message) -> None:
        projects = await sync_to_async(set)(models.Project.objects.all())
        for project in projects:
            if self.check_project(message, project):
                chat = await self.get_chat(message.chat.id)
                text = []

                if chat.title is not None:
                    title = f"[{chat.title}]({chat.invite_link})"
                else:
                    if chat.type == pyrogram.enums.ChatType.PRIVATE:
                        channel_object: models.Channel = await models.Channel.objects.aget(telegram_id = chat.id)
                        title = channel_object.name
                    elif chat.type == pyrogram.enums.ChatType.BOT:
                        title = f"[{message.from_user.first_name}](https://t.me/{message.from_user.username})"
                    else:
                        title = chat.invite_link
                text.append(f"Чат: {title}")
                text.append(f"Дата и время: {message.date}")

                if message.from_user is not None:
                    if message.from_user.is_bot:
                        author = f"[{message.from_user.first_name}](https://t.me/{message.from_user.username})"
                    else:
                        if message.from_user.first_name is not None:
                            username = message.from_user.first_name
                        elif message.from_user.last_name is not None:
                            username = message.from_user.last_name
                        else:
                            username = message.from_user.username
                        author = f"[{username}](tg://user?id={message.from_user.id})"
                    text.append(f"Автор: {author}")

                text.append("")
                text.append(message.text)
                await self.send_message(
                    project.post_channel,
                    "\n".join(text),
                    pyrogram.enums.ParseMode.MARKDOWN,
                    disable_web_page_preview = True
                )

    def check_project(self, message: pyrogram.types.Message, project: models.Project) -> bool:
        # todo: remove print
        print(message.text)
        check = False
        if message.text is None:
            text = ""
        else:
            text = message.text.lower()
        for keyword in project.keywords.split(self.settings.KEYWORD_SEPARATOR):
            if keyword.lower() in text:
                check = True
                break
        if check:
            for stop_word in project.stop_words.split(self.settings.STOP_WORD_SEPARATOR):
                if stop_word.lower() in text:
                    check = False
                    break
        return check


async def channel_filter(_, userbot: UserbotClient, query: pyrogram.types.Message) -> bool:
    return query.chat.id in userbot.channels


channel_filter = pyrogram.filters.create(channel_filter)


class Command(telegram_parser_command.TelegramParserCommand):
    def handle(self, *args, **options) -> None:
        asyncio.run(self.run())

    async def run(self) -> None:
        # создается папка для хранения сессий pyrogram
        Path(self.settings.PYROGRAM_SESSION_FOLDER).mkdir(parents = True, exist_ok = True)
        userbots: dict[str, pyrogram.Client] = {}
        channels = {x.telegram_id: x for x in await sync_to_async(set)(models.Channel.objects.all())}

        self.logger.info("Userbots are starting.")
        for user in await sync_to_async(list)(models.Userbot.objects.all()):
            userbot = await self.get_userbot(user, channels)
            userbots[user.phone] = userbot
            channels = {channel_id: channel for channel_id, channel in channels.items()
                        if channel_id not in userbot.channels}
        self.logger.info("All userbots were started.")
        if len(channels) > 0:
            self.logger.warning(f"Not tracking channels amount: {len(channels)}.")

        await pyrogram.idle()

        self.logger.info("Userbots are stopping.")
        for userbot in userbots.values():
            await userbot.stop()
        self.logger.info("All userbots were stopped.")

    async def get_userbot(self, user: models.Userbot, channels: dict[int, models.Channel]) -> UserbotClient:
        userbot = UserbotClient(
            user.name,
            self.settings.secrets.pyrogram.api_id,
            self.settings.secrets.pyrogram.api_hash,
            phone_number = user.phone,
            workdir = self.settings.PYROGRAM_SESSION_FOLDER
        )

        userbot.on_message(channel_filter)(userbot.track)
        await userbot.start()
        await userbot.prepare(channels)

        return userbot
