import logging

from secret_keeper import SecretKeeper
from .apps import TelegramParserConfig


class Settings:
    APP_NAME = TelegramParserConfig.name

    def __init__(self):
        self.PARSING_DATA_FOLDER = "parsing_data"

        # Пути секретов
        self.SECRETS_FOLDER = "secrets"

        self.DATABASE_SECRETS_FOLDER = f"{self.SECRETS_FOLDER}/database"
        self.DATABASE_CREDENTIALS_PATH = f"{self.DATABASE_SECRETS_FOLDER}/credentials.json"

        self.ADMIN_PANEL_SECRETS_FOLDER = f"{self.SECRETS_FOLDER}/admin_panel"
        self.ADMIN_USER_CREDENTIALS_PATH = f"{self.ADMIN_PANEL_SECRETS_FOLDER}/admin_user.json"

        self.DEVELOPER_SECRETS_FOLDER = f"{self.SECRETS_FOLDER}/developer"
        self.DEVELOPER_CREDENTIALS_PATH = f"{self.DEVELOPER_SECRETS_FOLDER}/credentials.json"

        self.PYROGRAM_SECRETS_FOLDER = f"{self.SECRETS_FOLDER}/pyrogram"
        self.PYROGRAM_CREDENTIALS_PATH = f"{self.PYROGRAM_SECRETS_FOLDER}/credentials.json"

        # Настройки логгера
        self.LOG_FORMAT = ("[%(asctime)s] - [%(levelname)s] - %(name)s -"
                           " (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
        self.LOG_FOLDER = "logs"
        self.CONSOLE_LOG_LEVEL = logging.DEBUG
        self.FILE_LOG_LEVEL = logging.DEBUG

        # Настройки pyrogram
        self.PYROGRAM_FOLDER = "pyrogram"
        self.PYROGRAM_SESSION_FOLDER = f"{self.PYROGRAM_FOLDER}/sessions"

        self.secrets = SecretKeeper(self)
