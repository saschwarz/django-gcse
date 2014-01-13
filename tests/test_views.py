from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.core.urlresolvers import reverse
from gcse.models import Label, Annotation


class ViewsTemplatesTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.ROOT_URLCONF = settings.ROOT_URLCONF
        self.TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS
        settings.TEMPLATE_CONTEXT_PROCESSORS = ()
        self.label = Label(name='name', description='description')
        self.label.save()
        self.annotation = Annotation(comment='Site Name', original_url='http://example.com/')
        self.annotation.save()
        self.annotation.labels.add(self.label)
        self.annotation.save()

    def tearDown(self):
        settings.ROOT_URLCONF = self.ROOT_URLCONF
        settings.TEMPLATE_CONTEXT_PROCESSORS = self.TEMPLATE_CONTEXT_PROCESSORS

    def test_annotations(self):
        response = self.client.get(reverse('cse_annotations'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/annotation.xml')

    def test_results(self):
        response = self.client.get(reverse('cse_results'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/results.html')

    def test_cse(self):
        response = self.client.get(reverse('cse'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/cse.xml')

    def test_map(self):
        response = self.client.get(reverse('cse_map'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/map.html')

    def test_browse(self):
        response = self.client.get(reverse('cse_browse'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/browse.html')

    def test_search(self):
        response = self.client.get(reverse('cse_search'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/search.html')

    def test_edit(self):
        response = self.client.get(reverse('cse_edit', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/edit.html')

    def test_view(self):
        response = self.client.get(reverse('cse_view', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/view.html')

    def test_browse_by_label(self):
        response = self.client.get(reverse('cse_browse_by_label'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/browse_by_label_tabbed.html')

    def test_browse_by_label_grid(self):
        response = self.client.get(reverse('cse_browse_by_label_grid', kwargs={"label":self.label.name}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/browse_by_label_grid.html')

    def test_directions(self):
        response = self.client.get(reverse('cse_directions', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/directions.html')

    def test_add(self):
        response = self.client.get(reverse('cse_add'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/edit.html')

    def test_thanks(self):
        response = self.client.get(reverse('cse_thanks'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'gcse/thanks.html')
