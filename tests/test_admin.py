import xml.sax
from django.test import TestCase
from django.test.utils import override_settings

from gcse import models, views


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

    # def testShouldHaveAddress(self):
    #     # have one label with a physical address so should pass
    #     self.assertTrue(self.annotation.shouldHaveAddress())


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
