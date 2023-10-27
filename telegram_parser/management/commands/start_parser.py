import asyncio
from pathlib import Path

import pyrogram
from asgiref.sync import sync_to_async

import secret_keeper
from telegram_parser import models, settings
from telegram_parser.management.commands import telegram_parser_command


class UserBot(pyrogram.Client):
    settings = settings.Settings()
    channels: dict[int, models.Channel]

    async def prepare(self, channels: dict[int, models.Channel]) -> None:
        # todo: добавить проверку подписок ботов на каналы
        # todo: добавить вступление в чаты, на которые не подписан
        self.channels = channels
        for channel in self.channels.values():
            channel.userbot = self
        if self.name is None:
            label = self.phone_number
        else:
            label = self.name
        await models.Channel.objects.filter(id__in = (x.id for x in self.channels.values())).aupdate(userbot = label)

    @staticmethod
    async def track(self: "UserBot", message: pyrogram.types.Message) -> None:
        projects = await sync_to_async(set)(models.Project.objects.all())
        for project in projects:
            if self.check(message, project):
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

                text.extend(
                    [
                        "",
                        message.text
                    ]
                )
                await self.send_message(
                    project.post_channel,
                    "\n".join(text),
                    pyrogram.enums.ParseMode.MARKDOWN,
                    disable_web_page_preview = True
                )

    def check(self, message: pyrogram.types.Message, project: models.Project) -> bool:
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


async def channel_filter(_, userbot: UserBot, query: pyrogram.types.Message) -> bool:
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
        for user in self.settings.secrets.pyrogram.userbots:
            userbot = await self.get_userbot(user, channels)
            await userbot.start()
            userbots[user["phone"]] = userbot
        self.logger.info("All userbots were started.")

        await pyrogram.idle()

        self.logger.info("Userbots are stopping.")
        for userbot in userbots.values():
            await userbot.stop()
        self.logger.info("All userbots were stopped.")

    # todo: зарегистрировать api_id и api_hash на заказчика
    async def get_userbot(self, user: secret_keeper.UserBot, channels: dict[int, models.Channel]) -> pyrogram.Client:
        userbot = UserBot(
            user["name"],
            self.settings.secrets.pyrogram.api_id,
            self.settings.secrets.pyrogram.api_hash,
            phone_number = user["phone"],
            workdir = self.settings.PYROGRAM_SESSION_FOLDER
        )
        # todo: распределять каналы по ботам равномерно?
        await userbot.prepare(channels)

        userbot.on_message(channel_filter)(userbot.track)
        return userbot
