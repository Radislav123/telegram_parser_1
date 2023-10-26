import asyncio
from pathlib import Path

import pyrogram

from secret_keeper import UserBot
from telegram_parser.management.commands import telegram_parser_command


class Command(telegram_parser_command.TelegramParserCommand):
    def handle(self, *args, **options) -> None:
        asyncio.run(self.run())

    async def run(self) -> None:
        # создается папка для хранения сессий pyrogram
        Path(self.settings.PYROGRAM_SESSION_FOLDER).mkdir(parents = True, exist_ok = True)
        userbots: list[pyrogram.Client] = []

        self.logger.info("Userbots are starting.")
        for user in self.settings.secrets.pyrogram.data:
            userbot = self.get_userbot(user)
            await userbot.start()
            userbots.append(userbot)
        self.logger.info("All userbots were started.")

        await pyrogram.idle()

        self.logger.info("Userbots are stopping.")
        for userbot in userbots:
            await userbot.stop()
        self.logger.info("All userbots were stopped.")

    # todo: зарегистрировать api_id и api_hash на заказчика
    def get_userbot(self, user: UserBot) -> pyrogram.Client:
        userbot = pyrogram.Client(
            user["name"],
            self.settings.secrets.pyrogram.api_id,
            self.settings.secrets.pyrogram.api_hash,
            phone_number = user["phone"],
            workdir = self.settings.PYROGRAM_SESSION_FOLDER
        )

        userbot.on_message(pyrogram.filters.text)(message_reply)
        userbot.on_message(pyrogram.filters.photo)(photo_reply)
        userbot.on_message()(reply)

        return userbot


async def reply(client, message) -> None:
    print(client)
    print(message)
    await message.reply("reply")


async def message_reply(client, message) -> None:
    await message.reply("message reply")


async def photo_reply(client, message) -> None:
    await message.reply("photo reply")
