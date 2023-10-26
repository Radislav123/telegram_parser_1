from telegram_parser import models
from telegram_parser.management.commands import create_admin


class Command(create_admin.Command):
    def handle(self, *args, **options) -> None:
        super().handle(*args, **options)
        self.fill_db()
        self.logger.info("Database was prepared for test.")

    def fill_db(self) -> None:
        channels = [
            models.Channel(
                name = channel["name"],
                telegram_id = channel["telegram_id"]
            ) for channel in self.settings.secrets.test_data.channels
        ]
        models.Channel.objects.bulk_create(
            channels,
            update_conflicts = True,
            update_fields = ["userbot"],
            unique_fields = ["telegram_id"]
        )

        projects = [
            models.Project(
                name = project["name"],
                keywords = self.settings.KEYWORD_SEPARATOR.join(project["keywords"]),
                stop_words = self.settings.STOP_WORD_SEPARATOR.join(project["stop_words"]),
                post_channel = project["post_channel"]
            ) for project in self.settings.secrets.test_data.projects
        ]
        models.Project.objects.bulk_create(
            projects,
            update_conflicts = True,
            update_fields = ["keywords", "stop_words", "post_channel"],
            unique_fields = ["name"]
        )
