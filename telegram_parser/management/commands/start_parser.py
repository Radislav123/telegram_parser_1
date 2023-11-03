import asyncio
import datetime
import random
import time
from pathlib import Path

import pyrogram.errors.exceptions
from asgiref.sync import sync_to_async

import logger
from telegram_parser import models, settings
from telegram_parser.management.commands import telegram_parser_command


def split(text: str, separators: set[str]) -> list[str]:
    splitted_text = [text]
    for separator in separators:
        splitted_text = text.split(separator)
        if len(splitted_text) > 1:
            break
    return [x.strip() for x in splitted_text]


class UserbotClient(pyrogram.Client):
    settings = settings.Settings()
    db_object: models.Userbot
    projects: list[models.Project]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.logger = logger.Logger(self.__class__.__name__)
        self.channels: dict[int, models.Channel] = {}

    async def prepare(self, channels: dict[int, models.Channel]) -> None:
        self.db_object = await models.Userbot.objects.aget(phone = self.phone_number)

        # проверка вступления в канал для пересылки
        self.projects = await sync_to_async(list)(models.Project.objects.all())
        await self.check_projects()

        # проверка вступления в каналы для мониторинга
        await self.check_channels(channels)

        # изменяется day_channels_join_counter
        await self.db_object.asave()

    async def check_projects(self) -> None:
        for project in self.projects:
            if not await models.UserbotProject.objects.filter(userbot = self.db_object, project = project).aexists():
                try:
                    chat = await self.get_chat(project.post_channel_link)
                    if project.post_channel_telegram_id is None:
                        project.post_channel_telegram_id = chat.id
                        await project.asave()
                    await self.get_chat_member(chat.id, "me")
                except AttributeError:
                    if self.db_object.day_channels_join_counter < self.settings.MAX_DAY_CHANNEL_JOINS:
                        self.db_object.last_channel_join_date = datetime.date.today()
                        try:
                            await self.join_chat(project.post_channel_link)
                            self.db_object.day_channels_join_counter += 1
                        except Exception as exception:
                            self.logger.exception(str(exception))
                await models.UserbotProject(userbot = self.db_object, project = project).asave()

    async def check_channels(self, channels: dict[int, models.Channel]) -> None:
        if self.db_object.last_channel_join_date < datetime.date.today():
            self.db_object.day_channels_join_counter = 0

        for channel in channels.values():
            if not await models.UserbotChannel.objects.filter(userbot = self.db_object, channel = channel).aexists():
                chat = await self.get_chat(channel.link)
                if channel.telegram_id is None:
                    channel.telegram_id = chat.id
                    await channel.asave()
                if chat.type != pyrogram.enums.ChatType.PRIVATE and chat.type != pyrogram.enums.ChatType.BOT:
                    try:
                        await self.get_chat_member(chat.id, "me")
                        self.channels[channel.telegram_id] = channel
                    except AttributeError:
                        if self.db_object.day_channels_join_counter < self.settings.MAX_DAY_CHANNEL_JOINS:
                            self.db_object.last_channel_join_date = datetime.date.today()
                            try:
                                await self.join_chat(channel.link)
                                self.db_object.day_channels_join_counter += 1
                                self.channels[channel.telegram_id] = channel
                            except Exception as exception:
                                self.logger.exception(str(exception))
                else:
                    self.channels[channel.telegram_id] = channel
                await models.UserbotChannel(userbot = self.db_object, channel = channel).asave()
            else:
                self.channels[channel.telegram_id] = channel

        await self.db_object.asave()

    @staticmethod
    async def track(self: "UserbotClient", message: pyrogram.types.Message) -> None:
        for project in self.projects:
            if self.check_project(message, project):
                chat = await self.get_chat(message.chat.id)
                text = ["➖➖➖➖➖➖➖➖➖➖"]

                if chat.title is not None:
                    title = f"[{chat.title}]({chat.invite_link})"
                else:
                    if chat.type == pyrogram.enums.ChatType.PRIVATE:
                        channel_object: models.Channel = await models.Channel.objects.aget(link = chat.invite_link)
                        title = channel_object.name
                    elif chat.type == pyrogram.enums.ChatType.BOT:
                        title = f"[{message.from_user.first_name}](https://t.me/{message.from_user.username})"
                    else:
                        title = chat.invite_link
                text.append(f"Чат: {title}")

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
                text.append("➖➖➖➖➖➖➖➖➖➖")

                await self.send_message(
                    project.post_channel_telegram_id,
                    "\n".join(text),
                    pyrogram.enums.ParseMode.MARKDOWN,
                    disable_web_page_preview = True
                )

    def check_project(self, message: pyrogram.types.Message, project: models.Project) -> bool:
        check = False
        if message.text is None:
            text = ""
        else:
            text = message.text.lower()
        for keyword in split(project.keywords, self.settings.KEYWORD_SEPARATORS):
            if keyword.lower() in text:
                check = True
                break
        if check:
            for stop_word in split(project.stop_words, self.settings.STOP_WORD_SEPARATORS):
                if stop_word.lower() in text:
                    check = False
                    break
        return check

    # переопределено для того, чтобы вводить код подтверждения не в консоль, а в панели администратора
    async def authorize(self) -> pyrogram.types.User:
        user_object: models.Userbot = await models.Userbot.objects.aget(phone = self.phone_number)
        sent_code = await self.send_code(self.phone_number)

        sent_code_descriptions = {
            pyrogram.enums.SentCodeType.APP: "Telegram app",
            pyrogram.enums.SentCodeType.SMS: "SMS",
            pyrogram.enums.SentCodeType.CALL: "phone call",
            pyrogram.enums.SentCodeType.FLASH_CALL: "phone flash call",
            pyrogram.enums.SentCodeType.FRAGMENT_SMS: "Fragment SMS",
            pyrogram.enums.SentCodeType.EMAIL_CODE: "email code"
        }
        print(
            f"The confirmation code has been sent via {sent_code_descriptions[sent_code.type]}"
            f" to {user_object.name} ({user_object.phone})"
        )

        while not user_object.verification_code:
            time.sleep(3)
            user_object: models.Userbot = await models.Userbot.objects.aget(phone = self.phone_number)
        else:
            self.phone_code = user_object.verification_code
            user_object.verification_code = None
            await user_object.asave()
            try:
                return await self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
            except pyrogram.errors.SessionPasswordNeeded:
                return await self.check_password(self.password)


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
        shuffled_userbots: list[models.Userbot] = await sync_to_async(list)(models.Userbot.objects.all())
        random.shuffle(shuffled_userbots)
        for user in shuffled_userbots:
            userbot = await self.get_userbot(user, channels)
            userbots[user.phone] = userbot
            channels = {telegram_id: channel for telegram_id, channel in channels.items()
                        if telegram_id not in userbot.channels}
        self.logger.info("All userbots were started.")
        if len(channels) > 0:
            self.logger.warning(f"Not tracking channels amount: {len(channels)}:")
            self.logger.warning(channels)

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
            workdir = self.settings.PYROGRAM_SESSION_FOLDER,
            password = user.cloud_password
        )

        userbot.on_message(channel_filter)(userbot.track)
        await userbot.start()
        await userbot.prepare(channels)

        return userbot
