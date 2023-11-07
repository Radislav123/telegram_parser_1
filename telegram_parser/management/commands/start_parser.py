import asyncio
import datetime
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
    db_object: models.Userbot = None
    projects: list[models.Project]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.logger = logger.Logger(self.__class__.__name__)
        self.channels: dict[int, models.Channel] = {}

    async def stop(self, *args, **kwargs) -> "UserbotClient":
        if self.db_object is not None:
            self.db_object.active = False
            await self.db_object.asave()
        return await super().stop(*args, **kwargs)

    async def prepare(self, channels: dict[int, models.Channel]) -> None:
        self.db_object = await models.Userbot.objects.aget(phone = self.phone_number)

        # проверка вступления в канал для пересылки
        self.projects = await sync_to_async(list)(models.Project.objects.all())
        await self.check_projects()

        # проверка вступления в каналы для мониторинга
        await self.check_channels(channels)

        # изменяется day_channels_join_counter
        await self.db_object.asave()

        self.db_object.active = True
        await self.db_object.asave()

    async def check_projects(self) -> None:
        for project in self.projects:
            if not await models.UserbotProject.objects.filter(userbot = self.db_object, project = project).aexists():
                try:
                    chat = await self.get_chat(project.post_channel_username)
                    if project.post_channel_telegram_id is None:
                        project.post_channel_telegram_id = chat.id
                        await project.asave()
                    await self.get_chat_member(chat.id, "me")
                except (AttributeError, pyrogram.errors.exceptions.UserNotParticipant):
                    if self.db_object.day_channels_join_counter < self.settings.MAX_DAY_CHANNEL_JOINS:
                        self.db_object.last_channel_join_date = datetime.date.today()
                        try:
                            await self.join_chat(project.post_channel_username)
                            self.db_object.day_channels_join_counter += 1
                        except Exception as exception:
                            self.logger.exception(str(exception))
                await models.UserbotProject(userbot = self.db_object, project = project).asave()

    async def check_channels(self, channels: dict[int, models.Channel]) -> None:
        if self.db_object.last_channel_join_date < datetime.date.today():
            self.db_object.day_channels_join_counter = 0

        for channel in channels.values():
            try:
                # этот бот уже вступал в этот канал
                if await models.UserbotChannel.objects.filter(userbot = self.db_object, channel = channel).aexists():
                    self.channels[channel.telegram_id] = channel
                # другой бот уже вступал в этот канал
                elif await models.UserbotChannel.objects.filter(channel = channel).aexists():
                    pass
                # никакой бот не вступал в этот канал
                else:
                    chat_preview: pyrogram.types.ChatPreview = await self.get_chat(channel.username)
                    if (chat_preview.type != pyrogram.enums.ChatType.PRIVATE and
                            chat_preview.type != pyrogram.enums.ChatType.BOT):
                        if self.db_object.day_channels_join_counter < self.settings.MAX_DAY_CHANNEL_JOINS:
                            self.db_object.last_channel_join_date = datetime.date.today()
                            try:
                                await self.join_chat(channel.username)
                                self.db_object.day_channels_join_counter += 1
                                await self.db_object.asave()
                                if channel.telegram_id is None:
                                    chat: pyrogram.types.Chat = await self.get_chat(channel.username)
                                    channel.telegram_id = chat.id
                                    await channel.asave()
                                self.channels[channel.telegram_id] = channel
                            except Exception as exception:
                                self.logger.exception(str(exception))
                    else:
                        self.channels[channel.telegram_id] = channel
                    await models.UserbotChannel(userbot = self.db_object, channel = channel).asave()
            except Exception as error:
                self.logger.exception(str(error))

    @staticmethod
    async def track(self: "UserbotClient", message: pyrogram.types.Message) -> None:
        for project in self.projects:
            if self.check_project(message, project):
                chat = await self.get_chat(message.chat.id)
                text = ["➖➖➖➖➖➖➖➖➖➖"]

                if chat.title is not None:
                    channel_object: models.Channel = await models.Channel.objects.aget(telegram_id = chat.id)
                    title = f"[{chat.title}]({channel_object.link})"
                else:
                    if chat.type == pyrogram.enums.ChatType.PRIVATE:
                        channel_object: models.Channel = await models.Channel.objects.aget(telegram_id = chat.id)
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
            prepared_keyword = keyword.lower().strip()
            if prepared_keyword != "" and prepared_keyword in text:
                check = True
                break
        if check:
            for stop_word in split(project.stop_words, self.settings.STOP_WORD_SEPARATORS):
                prepared_stop_word = stop_word.lower().strip()
                if prepared_stop_word != "" and prepared_stop_word in text:
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
            f" to {user_object.name} ({user_object.phone})."
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
        old_users = await sync_to_async(list)(models.Userbot.objects.all())
        for user in old_users:
            user.active = None
            await user.asave()

        # создается папка для хранения сессий pyrogram
        Path(self.settings.PYROGRAM_SESSION_FOLDER).mkdir(parents = True, exist_ok = True)
        userbots: dict[str, pyrogram.Client] = {}
        channels = {x.link: x for x in await sync_to_async(set)(models.Channel.objects.all())}

        self.logger.info("Userbots are starting.")
        for user in await sync_to_async(list)(models.Userbot.objects.all()):
            try:
                userbot = await self.get_userbot(user, channels)
                userbots[user.phone] = userbot
                channels = {link: channel for link, channel in channels.items()
                            if channel.telegram_id not in userbot.channels}
            except Exception as error:
                self.logger.warning(user.name)
                self.logger.warning(error)
        self.logger.info("All userbots were started.")
        if len(channels) > 0:
            self.logger.warning(f"Not tracking channels amount: {len(channels)}")
            self.logger.warning({username: channel for username, channel in channels.items()})

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
