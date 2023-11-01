import json
from typing import TYPE_CHECKING, TypedDict


if TYPE_CHECKING:
    from telegram_parser.settings import Settings

Userbot = TypedDict("Userbot", {"name": str, "phone": str, "cloud_password": str})
Channel = TypedDict("Channel", {"name": str, "telegram_id": int})
Project = TypedDict("Project", {"name": str, "keywords": list[str], "stop_words": list[str], "post_channel": int})


# todo: replace (inherit from) with one from parsing_helper
# todo: update one from parsing_helper with this one
class SecretKeeper:
    class Module:
        name: str
        secrets_path: str
        json: dict
        secret_keeper: "SecretKeeper"

        def get_dict(self) -> dict:
            return self.json

    class Database(Module):
        ENGINE: str
        NAME: str

    class ParserUser(Module):
        username: str
        email: str
        password: str

    class Developer(Module):
        pc_name: str

    class Pyrogram(Module):
        api_id: int
        api_hash: str

    class Django(Module):
        secret_key: str

    class TestData(Module):
        channels: list[Channel]
        projects: list[Project]
        userbots: dict[str, Userbot]

    database: Database
    admin_user: ParserUser
    developer: Developer
    pyrogram: Pyrogram
    django: Django
    test_data: TestData

    def __init__(self, settings: "Settings") -> None:
        self.add_module("database", settings.DATABASE_CREDENTIALS_PATH)
        self.add_module("admin_user", settings.ADMIN_USER_CREDENTIALS_PATH)
        self.add_module("developer", settings.DEVELOPER_CREDENTIALS_PATH)
        self.add_module("pyrogram", settings.PYROGRAM_CREDENTIALS_PATH)
        self.add_module("django", settings.DJANGO_CREDENTIALS_PATH)
        try:
            self.add_module("test_data", settings.TEST_DATA_PATH)
            self.prepare_test_data()
        except FileNotFoundError:
            pass

    def prepare_test_data(self) -> None:
        # до этого момента это list
        # noinspection PyTypeChecker
        userbots: list[Userbot] = self.test_data.userbots
        self.test_data.userbots = {x["phone"]: x for x in userbots}

    @staticmethod
    def read_json(path: str) -> dict:
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def add_module(self, name: str, secrets_path: str) -> None:
        json_dict = self.read_json(secrets_path)
        module = type(name, (self.Module,), json_dict)()
        module.name = name
        module.secrets_path = secrets_path
        module.json = json_dict
        module.secret_keeper = self
        setattr(self, name, module)
