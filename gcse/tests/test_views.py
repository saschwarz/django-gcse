from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.core.urlresolvers import reverse
from cse.models import Label, Annotation


class ViewsTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.ROOT_URLCONF = settings.ROOT_URLCONF
#        settings.ROOT_URLCONF = 'cse.tests.cse_test_urls'
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

    def test_index(self):
        response = self.client.get(reverse('cse_home'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'index.html')

    def test_annotations(self):
        response = self.client.get(reverse('cse_annotations'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/annotation.xml')

    def test_results(self):
        response = self.client.get(reverse('cse_results'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/results.html')

    def test_cse(self):
        response = self.client.get(reverse('cse'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/cse.xml')

    def test_map(self):
        response = self.client.get(reverse('cse_map'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/map.html')

    def test_browse(self):
        response = self.client.get(reverse('cse_browse'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/browse.html')

    def test_search(self):
        response = self.client.get(reverse('cse_search'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/search.html')

    def test_edit(self):
        response = self.client.get(reverse('cse_edit', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/edit.html')

    def test_view(self):
        response = self.client.get(reverse('cse_view', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/view.html')

    def test_browse_by_label(self):
        response = self.client.get(reverse('cse_browse_by_label'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/browse_by_label_tabbed.html')

    def test_browse_by_label_grid(self):
        response = self.client.get(reverse('cse_browse_by_label_grid', kwargs={"label":self.label.name}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/browse_by_label_grid.html')

    def test_directions(self):
        response = self.client.get(reverse('cse_directions', kwargs={"id":self.annotation.id}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/directions.html')

    def test_add(self):
        response = self.client.get(reverse('cse_add'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/edit.html')

    def test_thanks(self):
        response = self.client.get(reverse('cse_thanks'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/thanks.html')

    # speciality views that are unused

    def test_created(self):
        response = self.client.get(reverse('cse_created'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/list.html')

    def test_modified(self):
        response = self.client.get(reverse('cse_modified'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/list.html')

    def test_todo(self):
        response = self.client.get(reverse('cse_todo'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/todo.html')

    def test_random(self):
        response = self.client.get(reverse('cse_random', kwargs={"type":self.label.name}))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/table.html')

    def test_submitted(self):
        response = self.client.get(reverse('cse_submitted'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/list.html')

    def test_images(self):
        response = self.client.get(reverse('cse_images'))
        self.assertEquals(200, response.status_code)
        self.assertTemplateUsed(response, 'cse/images.html')
