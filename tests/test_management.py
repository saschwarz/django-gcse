# -*- coding: utf-8 -*-
"""
test_commands
-----------

Tests for `django-gcse` management commands.
"""
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
from django.test import TestCase
from django.core import management

from mock import Mock, patch
from gcse.models import CustomSearchEngine, Label, Annotation


class TestOPMLCommand(TestCase):

    def setUp(self):
        self.gcse = CustomSearchEngine.objects.create(gid="asdf")
        self.label = Label.objects.create(name='background',
                                          background=True)
        self.gcse.background_labels.add(self.label)

    def test_no_args_gives_error_message(self):
        with StringIO() as output:
            self.assertRaises(SystemExit, management.call_command, 'import_opml', stderr=output)
            self.assertTrue('Incorrect number of arguments.' in output.getvalue())

    def test_non_existent_cse_raises(self):
        with StringIO() as output:
            with StringIO() as infile:
                self.assertRaisesMessage(management.CommandError,
                                         'CustomSearchEngine "1234" does not exist',
                                         management.call_command,
                                         'import_opml', '1234', 'unknown', infile,
                                         stderr=output)
                self.assertFalse(output.getvalue())

    def test_non_existent_label_raises(self):
        with StringIO() as output:
            with StringIO() as infile:
                self.assertRaisesMessage(management.CommandError,
                                         'Background Label "unknown" does not exist for CSE "asdf"',
                                         management.call_command,
                                         'import_opml', 'asdf', 'unknown', infile,
                                         stderr=output)
                self.assertFalse(output.getvalue())

    def test_existing_label_not_in_cse_raises(self):
        label = Label.objects.create(name='unused_background_label',
                                          background=True)
        with StringIO() as output:
            with StringIO() as infile:
                self.assertRaisesMessage(management.CommandError,
                                         'Background Label "unused_background_label" does not exist for CSE "asdf"',
                                         management.call_command,
                                         'import_opml', 'asdf', 'unused_background_label', infile,
                                         stderr=output)
                self.assertFalse(output.getvalue())

    def test_add_annotation_successfully(self):
        with StringIO() as output:
            with StringIO() as infile:
                infile.write("""<?xml version="1.0"?>
<opml version="1.1">
  <head>
    <title>Planet Django</title>
    <dateModified>Sat, 08 Mar 2014 20:57:35 +0000</dateModified>
    <ownerName>Adomas Paltanavičius</ownerName>
    <ownerEmail>adomas.paltanavicius@gmail.com</ownerEmail>
  </head>
  <body>
    <outline type="rss" text="2General" xmlUrl="http://www.2general.com/blog/django.rss.html" title="2General: Django" />
  </body>
</opml>""")
                infile.seek(0)
                management.call_command('import_opml', 'asdf', 'background', infile,
                                        stdout=output)
                self.assertEqual('Successfully added Annotation "2General: Django http://www.2general.com/blog/django.rss.html"\n', output.getvalue())

    def test_existing_annotation_not_added(self):
        with StringIO() as output:
            with StringIO() as infile:
                infile.write("""<?xml version="1.0"?>
<opml version="1.1">
  <head>
    <title>Planet Django</title>
    <dateModified>Sat, 08 Mar 2014 20:57:35 +0000</dateModified>
    <ownerName>Adomas Paltanavičius</ownerName>
    <ownerEmail>adomas.paltanavicius@gmail.com</ownerEmail>
  </head>
  <body>
    <outline type="rss" text="2General" xmlUrl="http://www.2general.com/blog/django.rss.html" title="2General: Django" />
  </body>
</opml>""")
                infile.seek(0)
                Annotation.objects.create(comment="2General: Django",
                                          original_url="http://www.2general.com/blog/django.rss.html")
                management.call_command('import_opml', 'asdf', 'background', infile,
                                        stdout=output)
                self.assertEqual('Found existing Annotation "2General: Django http://www.2general.com/blog/django.rss.html"\n', output.getvalue())


class TestImportCommand(TestCase):

    def test_no_args_gives_error_message(self):
        with StringIO() as output:
            self.assertRaises(SystemExit, management.call_command, 'import_cse', stderr=output)
            self.assertTrue('Incorrect number of arguments.' in output.getvalue())

    @patch('gcse.models.CustomSearchEngine.from_url', Mock())
    @patch('gcse.models.CustomSearchEngine.save', Mock())
    def test_non_existent_cse_raises(self):
        with StringIO() as output:
            with StringIO() as infile:
                management.call_command('import_cse', 'http://example.com',
                                        stderr=output)
                self.assertFalse(output.getvalue())
                self.assertTrue(CustomSearchEngine.from_url.wasCalled)
                self.assertTrue(CustomSearchEngine.save.wasCalled)
