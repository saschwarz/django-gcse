from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings

from django.conf import settings
from django.core.urlresolvers import reverse
from gcse.models import CustomSearchEngine, Label, Annotation
from gcse.views import CSEAnnotations


class ViewsTemplatesTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.ROOT_URLCONF = settings.ROOT_URLCONF
        self.TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS
        settings.TEMPLATE_CONTEXT_PROCESSORS = ()

        self.label = Label(name='name', description='description')
        self.label.save()
        self.annotation = Annotation(comment='Site Name', 
                                     original_url='http://example.com/',
                                     status=Annotation.STATUS.active)
        self.annotation.save()
        self.annotation.labels.add(self.label)
        self.annotation.save()
        self.cse = CustomSearchEngine.objects.create(gid="g123-456-AZ0", title="CSE 1234568")
        self.cse.background_labels.add(self.label)
        self.cse.save()
        self.old_pagination = CSEAnnotations.paginate_by

    def tearDown(self):
        settings.ROOT_URLCONF = self.ROOT_URLCONF
        settings.TEMPLATE_CONTEXT_PROCESSORS = self.TEMPLATE_CONTEXT_PROCESSORS
        CSEAnnotations.paginate_by = self.old_pagination

    def _add_annotation(self):
        annotation = Annotation(comment='Site Name 2', 
                                original_url='http://example.com/',
                                status=Annotation.STATUS.active)
        annotation.save()
        annotation.labels.add(self.label)

    def test_annotations_xml(self):
        response = self.client.get(reverse('cse_annotations', args=(self.cse.gid, 1)))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="1" num="1" total="1">', count=1)

    def test_multiple_page_annotations_xml(self):
        self._add_annotation()
        CSEAnnotations.paginate_by = 1 # one per page

        response = self.client.get(reverse('cse_annotations', args=(self.cse.gid, 1)))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="1" num="1" total="2">', count=1)
        self.assertContains(response, '<Comment>Site Name</Comment>', count=1)

        # get page 2
        response = self.client.get(reverse('cse_annotations', args=(self.cse.gid, 2)))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="2" num="2" total="2">', count=1)
        self.assertContains(response, '<Comment>Site Name 2</Comment>', count=1)


    def test_cse_xml(self):
        response = self.client.get(reverse('cse', args=(self.cse.gid,)))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 
                            '<CustomSearchEngine id="g123-456-AZ0" language="en" encoding="utf-8" enable_suggest="true">')
        self.assertContains(response, 
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.0.xml"/>')

    def test_cse_xml_multiple_annotations(self):
        self._add_annotation()
        # force update of CSE... change to signal on Annotation insert/delete?
        with override_settings(GCSE_CONFIG={'NUM_FACET_ITEMS_PER_FACET': 2,
                                            'NUM_ANNOTATIONS_PER_FILE': 1}):
            response = self.client.get(reverse('cse', args=(self.cse.gid,)))

        self.assertEqual(200, response.status_code)
        self.assertContains(response, 
                            '<CustomSearchEngine id="g123-456-AZ0" language="en" encoding="utf-8" enable_suggest="true">')
        self.assertContains(response, 
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.0.xml"/>')
        self.assertContains(response, 
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.1.xml"/>')

#     def test_browse(self):
#         response = self.client.get(reverse('cse_browse'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/browse.html')

#     def test_search(self):
#         response = self.client.get(reverse('cse_search'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/search.html')

#     def test_results(self):
#         response = self.client.get(reverse('cse_results'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/results.html')

#     def test_edit(self):
#         response = self.client.get(reverse('cse_edit', kwargs={"id":self.annotation.id}))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/edit.html')

#     def test_view(self):
#         response = self.client.get(reverse('cse_view', kwargs={"id":self.annotation.id}))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/view.html')

#     def test_browse_by_label(self):
#         response = self.client.get(reverse('cse_browse_by_label'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/browse_by_label_tabbed.html')

#     def test_add(self):
#         response = self.client.get(reverse('cse_add'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/edit.html')

#     def test_thanks(self):
#         response = self.client.get(reverse('cse_thanks'))
#         self.assertEquals(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/thanks.html')
