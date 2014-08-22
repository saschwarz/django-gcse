from django.core.management.base import BaseCommand
from gcse.models import CustomSearchEngine


class Command(BaseCommand):
    args = 'url_to_cse_xml'
    help = 'Import XML feed into CustomSearchEngine including Annotations'

    def handle(self, *args, **options):
        if len(args) != 1:
            self.stderr.write("Incorrect number of arguments. import_cse " + Command.args)
            exit()
        url = args[0]
        cse = CustomSearchEngine.from_url(url, import_linked_annotations=True)
        cse.save()
