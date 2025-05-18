import json

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from app.models import Test, TestVersion, TestVersionProblem


class Command(BaseCommand):
    help = "Prepopulate TestVersionProblem with example problems from problems.json"

    def handle(self, *args, **options):
        # Load the fallback examples from problems.json.
        try:
            with open("problems.json", "r", encoding="utf-8") as f:
                data = json.load(f)  # data should be a list of dicts
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading problems.json: {e}"))
            return

        # Use an existing user (for example, the first user) as the author.
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("No user found in the database."))
            return

        # Create or get a 'dummy' test to attach our example TestVersionProblem objects.
        test, _ = Test.objects.get_or_create(
            author=user, name="Example Test", defaults={"is_saved": True, "title": "Example Test"}
        )

        # Create (or get) a dummy TestVersion to hold these example problems.
        test_version, _ = TestVersion.objects.get_or_create(
            test=test,
            version_number=0,  # Using 0 to indicate it's a dummy version for examples.
        )

        # data is a list, so iterate each item. Only handle "AVALDISED" topics for now.
        for item in data:
            if item.get("topic") != "AVALDISED":
                continue

            topic = item.get("topic", "")
            diff = item.get("difficulty", "")
            definition = item.get("definition", "")
            solution = item.get("solution", "[No solution provided]")

            # Avoid duplicates: check if there's already a matching record
            exists = TestVersionProblem.objects.filter(
                test_version=test_version, topic=topic, difficulty=diff, definition=definition
            ).exists()

            if not exists:
                TestVersionProblem.objects.create(
                    test_version=test_version,
                    topic=topic,
                    difficulty=diff,
                    definition=definition,
                    solution=solution,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created example for topic '{topic}', difficulty '{diff}'")
                )

        self.stdout.write(
            self.style.SUCCESS("TestVersionProblem examples prepopulated successfully.")
        )
