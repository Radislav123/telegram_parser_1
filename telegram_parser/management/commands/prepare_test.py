from telegram_parser import models
from telegram_parser.management.commands import create_admin, telegram_parser_command


class Command(telegram_parser_command.TelegramParserCommand):
    def handle(self, *args, **options) -> None:
        create_admin.Command().create_all_users()
        self.clear_db()
        self.fill_db()
        self.logger.info("Database was prepared for test.")

    @staticmethod
    def clear_db() -> None:
        models.UserbotChannel.objects.all().delete()
        models.UserbotProject.objects.all().delete()
        models.Channel.objects.all().delete()
        models.Userbot.objects.all().delete()
        models.Project.objects.all().delete()

    def fill_db(self) -> None:
        userbots = [
            models.Userbot(
                name = userbot["name"],
                phone = userbot["phone"],
                cloud_password = userbot["cloud_password"],
                day_channels_join_counter = 0
            ) for userbot in self.settings.secrets.test_data.userbots.values()
        ]
        models.Userbot.objects.bulk_create(userbots)

        channels = [
            models.Channel(
                name = channel["name"],
                link = channel["link"]
            ) for channel in self.settings.secrets.test_data.channels
        ]
        models.Channel.objects.bulk_create(channels)

        projects = [
            models.Project(
                name = project["name"],
                keywords = self.settings.KEYWORD_SEPARATORS[0].join(project["keywords"]),
                stop_words = self.settings.STOP_WORD_SEPARATORS[0].join(project["stop_words"]),
                post_channel_link = project["post_channel_link"]
            ) for project in self.settings.secrets.test_data.projects
        ]
        models.Project.objects.bulk_create(projects)
