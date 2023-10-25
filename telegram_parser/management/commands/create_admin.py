from django.contrib.auth import get_user_model

from secret_keeper import SecretKeeper
from telegram_parser.management.commands import telegram_parser_command


class Command(telegram_parser_command.TelegramParserCommand):
    def handle(self, *args, **options):
        creating_users = (self.settings.secrets.admin_user,)
        for user in creating_users:
            self.create(user)

    @staticmethod
    def create(user: SecretKeeper.ParserUser):
        user_model = get_user_model()
        users = user_model.objects.filter(username = user.username)
        if not users.exists():
            user_model.objects.create_superuser(**user.get_dict())
            print(f"The {user.username} was created.")
        else:
            admin = users[0]
            for key, value in user.get_dict().items():
                if key != "username":
                    setattr(admin, key, value)
            print(f"User {user.username} was updated.")
