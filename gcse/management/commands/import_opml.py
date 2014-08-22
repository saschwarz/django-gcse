from lxml import etree as ET
from django.core.management.base import BaseCommand, CommandError
from gcse.models import Annotation, CustomSearchEngine, Label


class Command(BaseCommand):
    args = 'gid background_label path_to_opml.xml'
    help = 'Import outline elements from the specified opml.xml into the specified CustomSearchEngine as Annotations labeled with the specified background filter label.'

    def handle(self, *args, **options):

        if len(args) != 3:
            self.stderr.write("Incorrect number of arguments. import_opml " + Command.args)
            exit()

        gid, label_name, opml_path = args
        try:
            cse = CustomSearchEngine.objects.get(gid=gid)
        except CustomSearchEngine.DoesNotExist:
            raise CommandError('CustomSearchEngine "%s" does not exist' % gid)

        try:
            label = Label.objects.get(name=label_name,
                                      background=True,
                                      background_cses=cse)
        except Label.DoesNotExist:
            raise CommandError('Background Label "%s" does not exist for CSE "%s""' % (label_name, gid))

        tree = ET.parse(opml_path)
        for outline in tree.xpath('//outline'):
            annotation, created = Annotation.objects.get_or_create(comment=outline.attrib['title'],
                                                                   original_url=outline.attrib['xmlUrl'])
            if created:
                annotation.status = Annotation.STATUS.active
                annotation.about = Annotation.guess_google_url(annotation.original_url)
                annotation.labels.add(label)
                annotation.save()

                self.stdout.write('Successfully added Annotation "%s"' % annotation)
            else:
                self.stdout.write('Found existing Annotation "%s"' % annotation)
