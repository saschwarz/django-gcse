from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings

from django.conf import settings
from django.core.urlresolvers import reverse
from gcse.models import CustomSearchEngine, Label, Annotation
from gcse.views import CSEAnnotations, AnnotationList


class ViewsTemplatesTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.ROOT_URLCONF = settings.ROOT_URLCONF
        self.TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS
        settings.TEMPLATE_CONTEXT_PROCESSORS = ()

        self.label = Label(name='name', description='description')
        self.label.save()
        self.annotation = Annotation(comment='A Site Name',
                                     original_url='http://example.com/',
                                     status=Annotation.STATUS.active)
        self.annotation.save()
        self.annotation.labels.add(self.label)
        self.annotation.save()
        self.cse = CustomSearchEngine.objects.create(gid="g123-456-AZ0",
                                                     title="CSE 1234568",
                                                     description="Description")
        self.cse.background_labels.add(self.label)
        self.cse.save()
        self.old_pagination = CSEAnnotations.paginate_by
        self.old_annotation_pagination = AnnotationList.paginate_by

    def tearDown(self):
        settings.ROOT_URLCONF = self.ROOT_URLCONF
        settings.TEMPLATE_CONTEXT_PROCESSORS = self.TEMPLATE_CONTEXT_PROCESSORS
        CSEAnnotations.paginate_by = self.old_pagination
        AnnotationList.paginate_by = self.old_annotation_pagination

    def _add_annotation(self, name):
        annotation = Annotation(comment=name,
                                original_url='http://example.com/',
                                status=Annotation.STATUS.active)
        annotation.save()
        annotation.labels.add(self.label)

    def test_cse_xml(self):
        response = self.client.get(reverse('gcse_cse', args=(self.cse.gid,)))
        self.assertEqual(200, response.status_code)
        self.assertContains(response,
                            '<CustomSearchEngine id="g123-456-AZ0" language="en" encoding="utf-8" enable_suggest="true">')
        self.assertContains(response,
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.0.xml"/>')

    def test_cse_xml_multiple_annotations(self):
        self._add_annotation('Site Name 2')
        # force update of CSE... change to signal on Annotation insert/delete?
        with override_settings(GCSE_CONFIG={'NUM_FACET_ITEMS_PER_FACET': 2,
                                            'NUM_ANNOTATIONS_PER_FILE': 1}):
            response = self.client.get(reverse('gcse_cse', args=(self.cse.gid,)))

        self.assertEqual(200, response.status_code)
        self.assertContains(response,
                            '<CustomSearchEngine id="g123-456-AZ0" language="en" encoding="utf-8" enable_suggest="true">')
        self.assertContains(response,
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.0.xml"/>')
        self.assertContains(response,
                            '<Include type="Annotations" href="//example.com/annotations/g123-456-AZ0.1.xml"/>')

    def test_cse_list_view(self):
        response = self.client.get(reverse('gcse_cse_list'))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_list.html')

        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, 'Description')
        self.assertContains(response, 'Page 1 of 1')

    def test_annotations_xml(self):
        response = self.client.get(reverse('gcse_annotations', args=(self.cse.gid, 1)))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="1" num="1" total="1">', count=1)

    def test_multiple_page_annotations_xml(self):
        self._add_annotation('Site Name 2')
        CSEAnnotations.paginate_by = 1 # one per page

        response = self.client.get(reverse('gcse_annotations', args=(self.cse.gid, 1)))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="1" num="1" total="2">', count=1)
        self.assertContains(response, '<Comment>A Site Name</Comment>', count=1)

        # get page 2
        response = self.client.get(reverse('gcse_annotations', args=(self.cse.gid, 2)))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')
        self.assertContains(response, '<Annotations start="2" num="2" total="2">', count=1)
        self.assertContains(response, '<Comment>Site Name 2</Comment>', count=1)

    def test_annotation_list_for_cse(self):
        response = self.client.get(reverse('gcse_cse_annotation_list', kwargs={'gid': self.cse.gid}))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_annotation_list.html')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, 'A Site Name')
        self.assertContains(response, 'Page 1 of 1')
        self.assertContains(response, 'class="selected"><a href="?q=A"')

    def test_annotation_list_one_page_defaults_to_querying_letter_A(self):
        response = self.client.get(reverse('gcse_annotation_list'))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation_list.html')
        self.assertContains(response, 'A Site Name')
        self.assertContains(response, 'Page 1 of 1')
        self.assertContains(response, 'class="selected"><a href="?q=A"')

    def test_annotation_list_first_of_two_pages_querying_letter_S(self):
        self._add_annotation('Site Name 2')
        self._add_annotation('Site Name 3')
        AnnotationList.paginate_by = 1

        response = self.client.get(reverse('gcse_annotation_list')+"?q=S")

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation_list.html')
        self.assertContains(response, 'Site Name 2')
        self.assertNotContains(response, 'Site Name 3')
        self.assertContains(response, 'Page 1 of 2')
        self.assertContains(response, 'class="selected"><a href="?q=S"')

    def test_annotation_list_second_of_two_pages_querying_letter_S(self):
        self._add_annotation('Site Name 2')
        self._add_annotation('Site Name 3')
        AnnotationList.paginate_by = 1
        response = self.client.get(reverse('gcse_annotation_list')+"?q=S&page=2")

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation_list.html')
        self.assertNotContains(response, 'Site Name 2')
        self.assertContains(response, 'Site Name 3')
        self.assertContains(response, 'Page 2 of 2')
        self.assertContains(response, 'class="selected"><a href="?q=S"')

    def test_custom_search_engine_list(self):
        response = self.client.get(reverse('gcse_cse_list'))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_list.html')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, 'Description', 2)
        self.assertContains(response, 'Page 1 of 1')
        self.assertContains(response, '/cses/g123-456-AZ0/')

    def test_custom_search_engine_detail(self):
        response = self.client.get(reverse('gcse_cse_detail', kwargs={'gid': self.cse.gid}))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_detail.html')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, 'Description', 1)
        self.assertContains(response, '/cses/g123-456-AZ0/')
        self.assertContains(response, "View this Custom Search Engine's 1 Annotations")
        self.assertContains(response, "/cses/g123-456-AZ0/labels/")
        self.assertContains(response, "View this Custom Search Engine's 0 Labels")

    def test_annotation_list(self):
        response = self.client.get(reverse('gcse_annotation_list'))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation_list.html')
        self.assertContains(response, 'There are 1 Annotations currently in the example.com database')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, 'A Site Name')
        self.assertContains(response, '/annotations/1/')
        self.assertContains(response, "/labels/1/")
        self.assertContains(response, "Page 1 of 1")
        self.assertContains(response, "disabled", 35)
        self.assertContains(response, "selected", 1)

    def test_annotation_detail(self):
        response = self.client.get(reverse('gcse_annotation_detail', kwargs={'id': self.annotation.id}))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation_detail.html')
        self.assertContains(response, '<h1>A Site Name</h1>')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, "active")
        self.assertContains(response, '/cses/g123-456-AZ0/')
        self.assertContains(response, "/labels/1/")
        self.assertContains(response, "FILTER")
        self.assertContains(response, "http://example.com/")

    def test_label_list(self):
        response = self.client.get(reverse('gcse_label_list'))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/label_list.html')
        self.assertContains(response, 'There are 1 Labels currently in the example.com database')
        self.assertContains(response, 'CSE 1234568')
        self.assertContains(response, '/cses/g123-456-AZ0/')
        self.assertContains(response, "/labels/1/")
        self.assertContains(response, "Page 1 of 1")

    def test_cse_label_list(self):
        response = self.client.get(reverse('gcse_cse_label_list', kwargs={'gid': self.cse.gid}))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_label_list.html')
        self.assertContains(response, 'There are 0 background Labels and 0 Facets associated with the')
        self.assertContains(response, 'CSE 1234568: All Labels')

    def test_label_detail(self):
        response = self.client.get(reverse('gcse_label_detail', kwargs={'id': self.label.id}))

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/label_detail.html')
        self.assertContains(response, '<h1>Label: name</h1>')
        self.assertContains(response, 'description')
        self.assertContains(response, 'False')
        self.assertContains(response, 'There are 1 Annotations currently in the example.com database with this Label.')
        self.assertContains(response, '/annotations/1/')
        self.assertContains(response, "/labels/1/")
        self.assertContains(response, "FILTER")
        self.assertContains(response, "Page 1 of 1")
        self.assertContains(response, "disabled", 35)
        self.assertContains(response, "selected", 1)

    def test_cse_label_detail(self):
        response = self.client.get(reverse('gcse_cse_label_detail', kwargs={'gid': self.cse.gid,
                                                                            'id': self.label.id}))


        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse_label_detail.html')
        self.assertContains(response, '<h1>CSE 1234568 - Label: name</h1>')
        self.assertContains(response, 'name')
        self.assertContains(response, 'False')
        self.assertContains(response, "FILTER")
        self.assertContains(response, 'There are 1 Annotations tagged with this Label in the')
        self.assertContains(response, '/cses/g123-456-AZ0/')
        self.assertContains(response, '/cses/g123-456-AZ0/annotations/')
        self.assertContains(response, "/annotations/1/")
        self.assertContains(response, "Page 1 of 1")
        self.assertContains(response, "disabled", 35)
        self.assertContains(response, "selected", 1)

#     def test_search(self):
#         response = self.client.get(reverse('gcse_search'))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/search.html')

#     def test_results(self):
#         response = self.client.get(reverse('gcse_results'))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/results.html')

#     def test_edit(self):
#         response = self.client.get(reverse('gcse_edit', kwargs={"id":self.annotation.id}))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/edit.html')

#     def test_view(self):
#         response = self.client.get(reverse('gcse_view', kwargs={"id":self.annotation.id}))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/view.html')

#     def test_browse_by_label(self):
#         response = self.client.get(reverse('gcse_browse_by_label'))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/browse_by_label_tabbed.html')

#     def test_add(self):
#         response = self.client.get(reverse('gcse_add'))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/edit.html')

#     def test_thanks(self):
#         response = self.client.get(reverse('gcse_thanks'))
#         self.assertEqual(200, response.status_code)
#         self.assertTemplateUsed(response, 'gcse/thanks.html')
