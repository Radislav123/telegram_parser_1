from django.contrib.auth import get_user_model
from django.contrib.auth import models as auth_models

from secret_keeper import SecretKeeper
from telegram_parser.management.commands import telegram_parser_command


class Command(telegram_parser_command.TelegramParserCommand):
    def handle(self, *args, **options) -> list[auth_models.User]:
        return [self.create_user(user) for user in (self.settings.secrets.admin_user,)]

    def create_user(self, user: SecretKeeper.ParserUser) -> auth_models.User:
        user_model = get_user_model()
        users = user_model.objects.filter(username = user.username)
        if not users.exists():
            user_object = user_model.objects.create_superuser(**user.get_dict())
            self.logger.info(f"The {user.username} was created.")
        else:
            user_object = users[0]
            for key, value in user.get_dict().items():
                if key != "username":
                    setattr(user_object, key, value)
            self.logger.info(f"User {user.username} was updated.")
        return user_object
