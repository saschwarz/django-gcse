import xml.sax
from django.test import TestCase
from django.test.utils import override_settings

from gcse import models, views


class AnnotationHandlerTest(TestCase):

    def testParseWithAmpersand(self):
        str = '''<Annotations file="./clubsxml">
  <Annotation about="www.luckydogagility.com/*">
      <Label name="_cse_kueofys2mdy" />
      <Label name="facility" />
      <AdditionalData attribute="original_url" value="http://www.luckydogagility.com/" />
      <Comment>Lucky Dog &amp; Friends Agility</Comment>
  </Annotation>
  </Annotations>
  '''
        curHandler = models.AnnotationSAXHandler()
        xml.sax.parseString(str, curHandler)
        # print curHandler.annotations
        self.assertEqual(len(curHandler.annotations), 1)
        # is ampersand no longer encoded?
        self.assertEqual(curHandler.annotations[0].comment, 'Lucky Dog & Friends Agility')

    def testWithMakeAnnotations(self):
        str = '''<Annotation about="www.google.com/cse/tools/makeannotations?url=http%3A%2F%2Fwww.pacngorec.com%2Fpacngorec_home.htm&amp;pattern=exact&amp;label=_cse_kueofys2mdy&amp;label=_csefeed_kueofys2mdy" timestamp="0x000451ea1aeb78b6" href="CqABd3d3Lmdvb2dsZS5jb20vY3NlL3Rvb2xzL21ha2Vhbm5vdGF0aW9ucz91cmw9aHR0cCUzQSUyRiUyRnd3dy5wYWNuZ29yZWMuY29tJTJGcGFjbmdvcmVjX2hvbWUuaHRtJnBhdHRlcm49ZXhhY3QmbGFiZWw9X2NzZV9rdWVvZnlzMm1keSZsYWJlbD1fY3NlZmVlZF9rdWVvZnlzMm1keRC28a3Xob2UAg" feed="true">
    <Label name="_cse_kueofys2mdy" />
    <Label name="equipment"/>
    <AdditionalData attribute="original_url" value="http://www.pacngorec.com/pacngorec_home.htm" />
    <Comment>Pac 'n Go</Comment>
  </Annotation>'''
        curHandler = models.AnnotationSAXHandler()
        xml.sax.parseString(str, curHandler)
        self.assertEqual(len(curHandler.annotations), 1)
        annotation = curHandler.annotations[0]
        self.assertEqual(2, len(annotation.labels.all()))

    def testWithErrorOnOriginalURL(self):
        str = '''<Annotation about="agilitynerd.com/*" timestamp="0x000420938c4e0bb7" href="ChFhZ2lsaXR5bmVyZC5jb20vKhC3l7jiuJKIAg">
    <Label name="_cse_kueofys2mdy" />
    <Label name="blog" />
    <Label name="video" />
    <AdditionalData attribute="original_url" value="http://agilitynerd.com/*" />
    <Comment>AgilityNerd</Comment>
  </Annotation>'''
        curHandler = models.AnnotationSAXHandler()
        xml.sax.parseString(str, curHandler)
        self.assertEqual(len(curHandler.annotations), 1)
        # make sure asterisk is removed from original_url
        annotation = curHandler.annotations[0]
        self.assertEqual(annotation.original_url, "http://agilitynerd.com/")


class PlaceTest(TestCase):
    def setUp(self):
        backgroundLabel = models.Label(name="background 1",
                                       description="background 1 desc",
                                       background=True)
        backgroundLabel.save()
        label1 = models.Label(name="label 1",
                              description="label 1 desc",
                              background=False)
        label1.save()
        self.annotation = models.Place(comment="Site Name",
                                            original_url="http://example.com")
        self.annotation.save()
        self.annotation.labels.add(backgroundLabel)
        self.annotation.labels.add(label1)
        self.assertTrue(self.annotation.labels.count() == 2)

    def allowNullURL(self):
        a = models.Place(comment="Site Name")
        a.save()

    def testHasAddress(self):
        self.assertFalse(self.annotation.hasAddress())
        # add attributes until it passes
        self.annotation.address1 = "100 main st"
        self.assertFalse(self.annotation.hasAddress())
        self.annotation.city = "Hometown"
        self.assertFalse(self.annotation.hasAddress())
        self.annotation.state = "Hometown"
        self.assertFalse(self.annotation.hasAddress())
        self.annotation.country = "USA"
        self.assertTrue(self.annotation.hasAddress())

    def testShouldHaveAddress(self):
        # have one label with a physical address so should pass
        self.assertTrue(self.annotation.shouldHaveAddress())


class ViewLabels(TestCase):

    class MockLabel:
        def __init__(self, name):
            self.name = name

    def setUp(self):
        self._all_labels = [ViewLabels.MockLabel('one'),
                            ViewLabels.MockLabel('two'),
                            ViewLabels.MockLabel('three')]

    def test_all_labels_to_bitmasks_all_in_dict(self):
        results = views._all_labels_to_bitmasks(self._all_labels)
        self.assertEqual(len(results), len(self._all_labels))

    def test_all_labels_to_bitmasks_zero_index_bitmask(self):
        results = views._all_labels_to_bitmasks(self._all_labels)
        # first entry in labels is bitmask 1
        self.assertEqual(results[self._all_labels[0].name], 1)

    def test_all_labels_to_bitmasks_one_index_bitmask(self):
        results = views._all_labels_to_bitmasks(self._all_labels)
        # second entry in labels is bitmask 2
        self.assertEqual(results[self._all_labels[1].name], 2)

    def test_all_labels_to_bitmasks_two_index_bitmask(self):
        results = views._all_labels_to_bitmasks(self._all_labels)
        # third entry in labels is bitmask 4
        self.assertEqual(results[self._all_labels[2].name], 4)
