# -*- coding: utf-8 -*-
"""
test_models
-----------

Tests for `django-gcse` model module.
"""
from __future__ import unicode_literals
from io import StringIO
from lxml import etree as ET
import mock

from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from gcse.models import CustomSearchEngine, CSESAXHandler, Label, FacetItem, Annotation, AnnotationSAXHandler

# Default CSE XML created by google
CSE_XML = b"""<CustomSearchEngine id="c12345-r678" creator="creatorid" keywords="" language="en" domain="www.google.com" safesearch="true" encoding="utf-8">
  <Title>AgilityNerd Site Search</Title>
  <Context>
    <BackgroundLabels>
      <Label name="_cse_c12345-r678" mode="FILTER"/>
      <Label name="_cse_exclude_c12345-r678" mode="ELIMINATE"/>
      <Label name="blogs" mode="BOOST" weight="0.8"/>
    </BackgroundLabels>
  </Context>
  <LookAndFeel code="2" resultsurl="http://agilitynerd.com/blog/googlesearch.index" adsposition="11" googlebranding="watermark" searchboxsize="31" resultswidth="500" element_layout="1" theme="1" custom_theme="true" text_font="Arial, sans-serif" url_length="full" element_branding="show" enable_cse_thumbnail="true" promotion_url_length="full" ads_layout="1">
    <Logo/>
    <Colors url="#008000" background="#FFFFFF" border="#336699" title="#0000FF" text="#000000" visited="#663399" light="0000FF" logobg="336699" title_hover="#0000CC" title_active="#0000CC"/>
    <Promotions title_color="#0000CC" title_visited_color="#0000CC" url_color="#008000" background_color="#FFFFFF" border_color="#336699" snippet_color="#000000" title_hover_color="#0000CC" title_active_color="#0000CC"/>
    <SearchControls input_border_color="#D9D9D9" button_border_color="#666666" button_background_color="#CECECE" tab_border_color="#E9E9E9" tab_background_color="#E9E9E9" tab_selected_border_color="#FF9900" tab_selected_background_color="#FFFFFF"/>
    <Results border_color="#FFFFFF" border_hover_color="#FFFFFF" background_color="#FFFFFF" background_hover_color="#FFFFFF" ads_background_color="#FDF6E5" ads_border_color="#FDF6E5"/>
  </LookAndFeel>
  <AdSense>
    <Client id="partner-pub-id"/>
  </AdSense>
  <EnterpriseAccount/>
  <ImageSearchSettings enable="true"/>
  <autocomplete_settings/>
  <cse_advance_settings enable_speech="true"/>
</CustomSearchEngine>"""

# Semi customized
FACETED_XML = b"""<GoogleCustomizations version="1.0">
  <CustomSearchEngine id="csekeystring" version="1.0" creator="anothercreatorid" encoding="utf-8" volunteers="false" keywords="" visible="true" top_refinements="4">
    <Title>AgilityNerd Dog Agility Search</Title>
    <Description>Search for Dog Agility topics, clubs, trainers, facilities, organizations and stores</Description>
    <Context refinementsTitle="Refine results for $q:">
      <Facet>
        <FacetItem title="Blogs">
          <Label name="blog" mode="BOOST"/>
        </FacetItem>
        <FacetItem title="Clubs">
          <Label name="club" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Equipment">
          <Label name="equipment" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Forums">
          <Label name="forum" mode="FILTER"/>
        </FacetItem>
      </Facet>
      <Facet>
        <FacetItem title="General">
          <Label name="general" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Organizations">
          <Label name="organization" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Services">
          <Label name="service" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Stores">
          <Label name="store" mode="FILTER"/>
        </FacetItem>
      </Facet>
      <Facet>
        <FacetItem title="Training">
          <Label name="training" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Training Facilities">
          <Label name="facility" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Video">
          <Label name="video" mode="FILTER"/>
        </FacetItem>
        <FacetItem title="Ring Rental">
          <Label name="rental" mode="FILTER"/>
        </FacetItem>
      </Facet>
      <BackgroundLabels>
        <Label name="_cse_csekeystring" mode="FILTER" weight="1.0"/>
        <Label name="_cse_exclude_csekeystring" mode="ELIMINATE" weight="1.0"/>
      </BackgroundLabels>
    </Context>
    <LookAndFeel>
      <Logo url="http://data.agilitynerd.com/images/AgilityNerd_SideBySide.gif" destination="http://agilitynerd.com" height="51"/>
    </LookAndFeel>
    <SubscribedLinks/>
    <AdSense/>
    <EnterpriseAccount/>
  </CustomSearchEngine>
  <Include type="Annotations" href="http://googility.com/googility_annotations.xml"/>
</GoogleCustomizations>"""

ANNOTATION_XML = b"""<Annotations start="0" num="7" total="7">
  <Annotation about="tech.agilitynerd.com/author/" timestamp="0x0004d956807a35fd" href="Chx0ZWNoLmFnaWxpdHluZXJkLmNvbS9hdXRob3IvEP3r6IPoqrYC">
    <Label name="_cse_exclude_keystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com/author/" />
  </Annotation>
  <Annotation about="tech.agilitynerd.com/archives.html" timestamp="0x0004d9567c1f41da" href="CiJ0ZWNoLmFnaWxpdHluZXJkLmNvbS9hcmNoaXZlcy5odG1sENqD_eDnqrYC">
    <Label name="_cse_exclude_keystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com/archives.html" />
  </Annotation>
  <Annotation about="tech.agilitynerd.com/category/" timestamp="0x0004d829da16938d" href="Ch50ZWNoLmFnaWxpdHluZXJkLmNvbS9jYXRlZ29yeS8Qjafa0J2FtgI">
    <Label name="_cse_exclude_keystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com/category/" />
  </Annotation>
  <Annotation about="tech.agilitynerd.com/tag/" timestamp="0x0004d829d8c7d8fd" href="Chl0ZWNoLmFnaWxpdHluZXJkLmNvbS90YWcvEP2xn8adhbYC">
    <Label name="_cse_exclude_keystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com/tag/" />
  </Annotation>
  <Annotation about="tech.agilitynerd.com/*" score="1" timestamp="0x0004d825f3ed22b2" href="ChZ0ZWNoLmFnaWxpdHluZXJkLmNvbS8qELLFtJ_fhLYC">
    <Label name="_cse_adifferentkeystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com" />
  </Annotation>
  <Annotation about="tech.agilitynerd.com/*">
    <Label name="_cse_keystring" />
    <AdditionalData attribute="original_url" value="tech.agilitynerd.com/*" />
    <Comment>here's a comment</Comment>
  </Annotation>
</Annotations>"""


class TestCustomSearchEngine(TestCase):

    def test_adding_background_labels(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search'
                                 )
        cse.save()
        l1 = Label(name="keystring",
                   mode=Label.MODE.filter)
        l1.save()
        cse.background_labels.add(l1)

        l2 = Label(name="exclude_keystring",
                   mode=Label.MODE.eliminate)
        l2.save()
        cse.background_labels.add(l2)


class TestImportCustomSearchEngine(TestCase):

    def test_insert(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search'
                                 )
        cse.save()

    def test_gid_is_unique(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search'
                                 )
        cse.save()
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search'
                                 )
        self.assertRaises(IntegrityError, cse.save)

    def test_gid_creator_populated_from_google_xml_as_string(self):
        cse = CustomSearchEngine.from_string(CSE_XML)
        self.assertEqual("c12345-r678", cse.gid)
        self.assertEqual("creatorid", cse.creator)


def _extractPath(xml, path):
    doc = ET.fromstring(xml)
    return doc.xpath(path)

def _extractPathElementText(xml, path):
    rowset = _extractPath(xml, path)
    if rowset:
        return rowset[0].text
    return None

def _extractPathAsString(xml, path):
    rowset = _extractPath(xml, path)
    if rowset:
        return ET.tostring(rowset[0], encoding="unicode").strip()
    return ''


class TestCSEUpdateXML(TestCase):

    def test_output_xml_has_new_gid_when_no_changes_to_instance(self):
        cse = CustomSearchEngine(gid="c12345-r999",
                                 input_xml=CSE_XML)
        cse.save()
        self.assertEqual('c12345-r999',
                         _extractPath(cse.output_xml,
                                      "/GoogleCustomizations/CustomSearchEngine")[0].attrib['id'])

        self.assertEqual('', cse.title) # no title set so leave XML alone
        self.assertEqual("AgilityNerd Site Search",
                         _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_title_when_title_is_changed(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 input_xml=CSE_XML)
        cse.save()
        self.assertEqual(cse.title,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_title_element_when_there_is_no_title_element(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()
        self.assertEqual(cse.title,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_description_when_description_is_changed(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=CSE_XML)
        cse.save()
        self.assertEqual(cse.description,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Description"))

    def test_output_xml_has_new_description_element_when_there_is_no_description_element(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()

        self.assertEqual(cse.description,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Description"))

    def test_output_xml_has_new_title_and_description_when_neither_exist(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()

        self.assertEqual(cse.title,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Title"))
        self.assertEqual(cse.description,
                         _extractPathElementText(cse.output_xml,
                                                 "/GoogleCustomizations/CustomSearchEngine/Description"))

    def test_output_xml_has_annotation_include(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.save()

        self.assertEqual(1,
                         len(_extractPath(cse.output_xml,
                                          "/GoogleCustomizations/Include")))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.0.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include"))

    def test_output_xml_has_annotation_includes(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.annotation_count = lambda: 2000
        cse.save()

        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          "/GoogleCustomizations/Include")))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.0.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include[1]"))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.1.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include[2]"))

    def test_output_xml_has_new_facet_labels(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.save()
        label = Label(name="Dogs",
                      description="Dog refinement",
                      mode=Label.MODE.filter,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Dogs",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        label = Label(name="Cats",
                      description="Cat refinement",
                      mode=Label.MODE.filter,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Cats",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        cse.save()
        self.assertEqual(1,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet")))
        self.assertEqual(cse.facetitem_set.all()[0].xml(),
                         _extractPathAsString(cse.output_xml,
                                              ".//Context/Facet/FacetItem"))

    def test_output_xml_has_new_facet_labels(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.save()
        label = Label(name="Dogs",
                      description="Dog refinement",
                      mode=Label.MODE.filter,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Dogs",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        label = Label(name="Cats",
                      description="Cat refinement",
                      mode=Label.MODE.filter,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Cats",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        cse.save()
        self.assertEqual(1,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet")),
                         "should be only one Facet")
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet/FacetItem")),
                         "should be two FacetItems in Facet")
        self.assertEqual(cse.facetitem_set.all()[0].xml(),
                         _extractPathAsString(cse.output_xml,
                                              ".//Context/Facet/FacetItem[1]"),
                         "first FacetItem should be first")
        self.assertEqual(cse.facetitem_set.all()[1].xml(),
                         _extractPathAsString(cse.output_xml,
                                              ".//Context/Facet/FacetItem[2]"))

    def test_output_xml_num_facet_items_per_facet(self):
        cse = CustomSearchEngine.from_string(FACETED_XML)
        cse.save()
        with override_settings(GCSE_CONFIG={'NUM_FACET_ITEMS_PER_FACET': 2,
                                            'NUM_ANNOTATIONS_PER_FILE': 1000}):
            cse.save()

        self.assertEqual(6,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[1]/FacetItem")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[2]/FacetItem")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[3]/FacetItem")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[4]/FacetItem")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[5]/FacetItem")))
        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          ".//Context/Facet[6]/FacetItem")))
        self.assertEqual(cse.facetitem_set.all()[0].xml(),
                         _extractPathAsString(cse.output_xml,
                                              ".//Context/Facet[1]/FacetItem[1]"))
        self.assertEqual(cse.facetitem_set.all()[1].xml(),
                         _extractPathAsString(cse.output_xml,
                                              ".//Context/Facet[1]/FacetItem[2]"))

    def test_missing_google_customizations(self):
        xml = "<CustomSearchEngine/>"
        doc = ET.fromstring(xml)
        new_doc = CustomSearchEngine._add_google_customizations(doc)
        self.assertEqual("GoogleCustomizations", new_doc.tag)

    def test_has_google_customizations(self):
        xml = "<GoogleCustomizations/>"
        doc = ET.fromstring(xml)
        new_doc = CustomSearchEngine._add_google_customizations(doc)
        self.assertEqual("GoogleCustomizations", new_doc.tag)


class TestCSESAXHandler(TestCase):

    def setUp(self):
        self.handler = CSESAXHandler()
        self.cse, self.annotation_urls = self.handler.parseString(CSE_XML)

    def test_gid_is_parsed_from_xml(self):
        self.assertEqual('c12345-r678', self.cse.gid)

    def test_title_is_parsed_from_xml(self):
        self.assertEqual('AgilityNerd Site Search', self.cse.title)

    def test_empty_description_is_parsed_from_xml(self):
        self.assertEqual('', self.cse.description)

    def test_description_is_parsed_from_xml(self):
        self.cse, annotation_urls = self.handler.parseString(FACETED_XML)
        self.assertEqual(u'Search for Dog Agility topics, clubs, trainers, facilities, organizations and stores',
                         self.cse.description)

    def test_labels_are_parsed_from_xml(self):
        cse = self.cse
        self.assertEqual(0, cse.facetitem_set.count())
        self.assertEqual(3, cse.background_labels.count())

        labels = cse.background_labels.all()
        label_names = [x.name for x in labels]
        self.assertTrue("_cse_c12345-r678" in label_names)
        self.assertTrue("_cse_exclude_c12345-r678" in label_names)

        label_modes = [x.mode for x in labels]
        self.assertTrue(Label.MODE.filter in label_modes)
        self.assertTrue(Label.MODE.eliminate in label_modes)
        self.assertTrue(Label.MODE.boost in label_modes)

        self.assertEqual(True, labels[0].background)
        self.assertEqual(True, labels[1].background)
        self.assertEqual(True, labels[2].background)

        self.assertEqual(None, labels[0].weight)
        self.assertEqual(None, labels[1].weight)
        self.assertEqual(0.8, labels[2].weight)

    def test_labels_are_parsed_from_facets_in_xml(self):
        self.cse, annotation_urls = self.handler.parseString(FACETED_XML)
        cse = self.cse
        self.assertEqual(12, cse.facetitem_set.count())
        self.assertEqual(12, len(cse.facet_item_labels_counts()))
        labels = cse.facet_item_labels()
        label_names = set([x.name for x in labels])
        self.assertEqual(set(["blog", "club", "equipment", "forum", "general", "organization", "service", "store", "training", "facility", "video", "rental"]),
                         label_names)

        label_modes = [x.mode for x in labels]
        self.assertTrue(Label.MODE.filter in label_modes)
        self.assertFalse(Label.MODE.eliminate in label_modes)
        self.assertTrue(Label.MODE.boost in label_modes)

        self.assertEqual(set(["_cse_csekeystring", "_cse_exclude_csekeystring"]),
                         set([x.name for x in cse.background_labels.all()]))

    def test_input_xml_is_parsed_from_xml(self):
        expected = CSE_XML
        self.assertEqual(expected,
                         self.cse.input_xml)

    def test_facet_items_are_parsed_from_xml(self):
        cse, annotation_urls = self.handler.parseString(FACETED_XML)
        self.assertEqual(12, cse.facetitem_set.count())

    def test_no_annotation_includes_are_parsed_from_xml(self):
        cse, annotation_urls = self.handler.parseString(CSE_XML)
        self.assertEqual(0, len(annotation_urls))

    def test_annotation_includes_are_parsed_from_xml(self):
        cse, annotation_urls = self.handler.parseString(FACETED_XML)
        self.assertEqual(1, len(annotation_urls))


class TestLabel(TestCase):

    def test_get_mode(self):
        self.assertEqual(Label.MODE.eliminate, Label.get_mode("ELIMINATE"))
        self.assertEqual(Label.MODE.filter, Label.get_mode("FILTER"))
        self.assertEqual(Label.MODE.boost, Label.get_mode("BOOST"))

    def test_xml_weight_not_displayed_when_no_weight_specified(self):
        label = Label(name="blog")
        self.assertEqual('<Label name="blog" mode="FILTER"/>',
                         label.xml())

    def test_xml_weight_not_displayed_when_weight_specified_and_not_requested(self):
        label = Label(name="blog",
                      weight=0.5)
        self.assertEqual('<Label name="blog" mode="FILTER"/>',
                         label.xml(complete=False))

    def test_xml_weight_is_displayed(self):
        label = Label(name="blog",
                      weight=0.4)
        self.assertEqual('<Label name="blog" mode="FILTER" weight="0.4"/>',
                         label.xml())


class TestCSEAddingAnnotations(TestCase):

    def setUp(self):
        self.cse = CustomSearchEngine.from_string(FACETED_XML)

    def test_annotation_with_STATUS_ACTIVE_without_labels_not_in_cse(self):
        Annotation.objects.create(comment="Active Annotation",
                                  status=Annotation.STATUS.active)
        self.assertEqual(0, self.cse.annotation_count())

    def test_annotation_with_STATUS_ACTIVE_without_matching_label_not_in_cse(self):
        annotation = Annotation.objects.create(comment="Active Annotation",
                                               status=Annotation.STATUS.active)
        label = Label.objects.create()
        annotation.labels.add(label)
        annotation.save()
        self.assertEqual(0, self.cse.annotation_count())

    def test_annotation_with_matching_label_and_STATUS_SUBMITTED_not_in_cse(self):
        annotation = Annotation.objects.create(comment="Active Annotation",
                                               status=Annotation.STATUS.submitted)
        annotation.labels.add(self.cse.background_labels.all()[0])
        annotation.save()
        self.assertEqual(0, self.cse.annotation_count())

    def test_annotation_with_matching_label_and_STATUS_DELETED_not_in_cse(self):
        annotation = Annotation.objects.create(comment="Active Annotation",
                                               status=Annotation.STATUS.deleted)
        annotation.labels.add(self.cse.background_labels.all()[0])
        annotation.save()
        self.assertEqual(0, self.cse.annotation_count())

    def test_annotation_with_matching_label_and_STATUS_ACTIVE_in_cse(self):
        annotation = Annotation.objects.create(comment="Active Annotation",
                                               status=Annotation.STATUS.active)
        annotation.labels.add(self.cse.background_labels.all()[0])
        annotation.save()
        self.assertEqual(1, self.cse.annotation_count())
        self.assertEqual(self.cse.annotations()[0],
                         annotation)

# TODO move to googility
# class TestCSEAddingPlaces(TestCase):

#     def setUp(self):
#         self.cse = CustomSearchEngine.from_string(FACETED_XML)

#     def test_place_with_STATUS_ACTIVE_without_labels_not_in_cse(self):
#         Place.objects.create(comment="Active Place",
#                              status=Annotation.STATUS.active)
#         self.assertEqual(0, self.cse.annotation_count())

#     def test_place_with_STATUS_ACTIVE_without_matching_label_not_in_cse(self):
#         place = Place.objects.create(comment="Active Place",
#                                      status=Annotation.STATUS.active)
#         label = Label.objects.create()
#         place.labels.add(label)
#         place.save()
#         self.assertEqual(0, self.cse.annotation_count())

#     def test_place_with_matching_label_and_STATUS_SUBMITTED_not_in_cse(self):
#         place = Place.objects.create(comment="Active Place",
#                                      status=Annotation.STATUS.submitted)
#         place.labels.add(self.cse.background_labels.all()[0])
#         place.save()
#         self.assertEqual(0, self.cse.annotation_count())

#     def test_place_with_matching_label_and_STATUS_DELETED_not_in_cse(self):
#         place = Place.objects.create(comment="Active Place",
#                                      status=Annotation.STATUS.deleted)
#         place.labels.add(self.cse.background_labels.all()[0])
#         place.save()
#         self.assertEqual(0, self.cse.annotation_count())

#     def test_place_with_matching_label_and_STATUS_ACTIVE_in_cse(self):
#         place = Place.objects.create(comment="Active Place",
#                                      status=Annotation.STATUS.active)
#         place.labels.add(self.cse.background_labels.all()[0])
#         place.save()
#         self.assertEqual(1, self.cse.annotation_count())
#         self.assertEqual(self.cse.annotations()[0],
#                          place)


class TestAnnotationManager(TestCase):

    def test_manager_annotations(self):
        active = Annotation.objects.create(comment="Active Annotation",
                                           status=Annotation.STATUS.active)
        submitted = Annotation.objects.create(comment="Submitted Annotation",
                                              status=Annotation.STATUS.submitted)
        deleted = Annotation.objects.create(comment="Deleted Annotation",
                                            status=Annotation.STATUS.deleted)

        self.assertEqual(1, Annotation.objects.active().count())
        self.assertEqual(active, Annotation.objects.active().all()[0])
        self.assertEqual(1, Annotation.objects.submitted().count())
        self.assertEqual(submitted, Annotation.objects.submitted().all()[0])
        self.assertEqual(1, Annotation.objects.deleted().count())
        self.assertEqual(deleted, Annotation.objects.deleted().all()[0])

    # def test_manager_places(self):
    #     active = Place.objects.create(comment="Active Place",
    #                                   status=Annotation.STATUS.active)
    #     submitted = Place.objects.create(comment="Submitted Place",
    #                                      status=Annotation.STATUS.submitted)
    #     deleted = Place.objects.create(comment="Deleted Place",
    #                                    status=Annotation.STATUS.deleted)

    #     self.assertEqual(1, Annotation.objects.active().count())
    #     self.assertEqual(active, Annotation.objects.active().all()[0])
    #     self.assertEqual(1, Annotation.objects.submitted().count())
    #     self.assertEqual(submitted, Annotation.objects.submitted().all()[0])
    #     self.assertEqual(1, Annotation.objects.deleted().count())
    #     self.assertEqual(deleted, Annotation.objects.deleted().all()[0])


class TestAnnotationParsing(TestCase):

    def setUp(self):
        self.handler = AnnotationSAXHandler()

    def test_empty_annotations_produces_no_annotations(self):
        self.assertEqual([], self.handler.parseString('<Annotations></Annotations>'))

    def test_parse_annotations_from_string(self):
        annotations = Annotation.from_string(ANNOTATION_XML)
        self._validate(annotations)

    def test_parse_annotations_using_sax_handler(self):
        annotations = self.handler.parseString(ANNOTATION_XML)
        self._validate(annotations)

    def _validate(self, annotations):
        self.assertEqual(6, len(annotations))

        a0 = annotations[0]
        self.assertEqual("tech.agilitynerd.com/author/", a0.about)
        self.assertEqual("tech.agilitynerd.com/author/", a0.original_url)
        self.assertEqual("", a0.comment)
        self.assertEqual("_cse_exclude_keystring", a0.labels.all()[0].name)

        a1 = annotations[1]
        self.assertEqual("tech.agilitynerd.com/archives.html", a1.about)
        self.assertEqual("tech.agilitynerd.com/archives.html", a1.original_url)
        self.assertEqual("", a1.comment)
        self.assertEqual("_cse_exclude_keystring", a1.labels.all()[0].name)

        a2 = annotations[2]
        self.assertEqual("tech.agilitynerd.com/category/", a2.about)
        self.assertEqual("tech.agilitynerd.com/category/", a2.original_url)
        self.assertEqual("", a2.comment)
        self.assertEqual("_cse_exclude_keystring", a2.labels.all()[0].name)

        a3 = annotations[3]
        self.assertEqual("tech.agilitynerd.com/tag/", a3.about)
        self.assertEqual("tech.agilitynerd.com/tag/", a3.original_url)
        self.assertEqual("", a3.comment)
        self.assertEqual("_cse_exclude_keystring", a3.labels.all()[0].name)

        a4 = annotations[4]
        self.assertEqual("tech.agilitynerd.com/*", a4.about)
        # strip trailing asterisk
        self.assertEqual("tech.agilitynerd.com", a4.original_url)
        self.assertEqual("", a4.comment)
        self.assertEqual("_cse_adifferentkeystring", a4.labels.all()[0].name)

        a5 = annotations[5]
        self.assertEqual("tech.agilitynerd.com/*", a5.about)
        # strip trailing asterisk
        self.assertEqual("tech.agilitynerd.com/", a5.original_url)
        self.assertEqual("here's a comment", a5.comment)
        self.assertEqual(Annotation.STATUS.active, a5.status)
        self.assertEqual("_cse_keystring", a5.labels.all()[0].name)


class AnnotationSAXHandlerTests(TestCase):

    def testParseWithAmpersand(self):
        xml = '''<Annotations file="./clubsxml">
  <Annotation about="www.luckydogagility.com/*">
      <Label name="_cse_kueofys2mdy" />
      <Label name="facility" />
      <AdditionalData attribute="original_url" value="http://www.luckydogagility.com/" />
      <Comment>Lucky Dog &amp; Friends Agility</Comment>
  </Annotation>
  <Annotation about="agilitynerd.com/blog/*">
      <Label name="_cse_kueofys2mdy" />
      <Label name="blog" />
      <AdditionalData attribute="original_url" value="http://agilitynerd.com/blog/" />
      <Comment>AgilityNerd Dog Agility Blog</Comment>
  </Annotation>
  </Annotations>'''
        curHandler = AnnotationSAXHandler()
        annotations = curHandler.parseString(xml)
        self.assertEqual(len(annotations), 2)
        # is ampersand no longer encoded?
        annotation = annotations[0]
        self.assertEqual(annotation.comment, 'Lucky Dog & Friends Agility')
        self.assertEqual(annotation.original_url, 'http://www.luckydogagility.com/')
        self.assertEqual(annotation.about, 'www.luckydogagility.com/*')

        annotation = annotations[1]
        self.assertEqual(annotation.comment, 'AgilityNerd Dog Agility Blog')
        self.assertEqual(annotation.original_url, 'http://agilitynerd.com/blog/')
        self.assertEqual(annotation.about, 'agilitynerd.com/blog/*')


class AnnotationsLabelsLinks(TestCase):

    def setUp(self):
        active = Annotation.objects.create(comment="Active Annotation",
                                           status=Annotation.STATUS.active)
        label = Label.objects.create(name="Label & Name",
                                     background=False)
        active.labels.add(label)
        label = Label.objects.create(name="Background Label",
                                     background=True)
        active.labels.add(label)
        self.annotation = active

    def test_labels_as_links_shows_all_labels(self):
        self.assertEqual('<a class="label-link" href="/labels/2/">Background Label</a><a class="label-link" href="/labels/1/">Label & Name</a>',
                         self.annotation.labels_as_links())

    def test_labels_as_links_hides_background_labels(self):
        self.assertEqual('<a class="label-link" href="/labels/1/">Label & Name</a>',
                         self.annotation.labels_as_links(include_background_labels=False))


class AnnotationsLabels(TestCase):

    def test_guess_google_url_for_a_single_page(self):
        self.assertEqual('example.com/foo.html',
                         Annotation.guess_google_url("http://example.com/foo.html"))

    def test_guess_google_url_for_a_terminated_path(self):
        self.assertEqual('example.com/foo/*',
                         Annotation.guess_google_url("http://example.com/foo/"))

    def test_guess_google_url_for_a_nonterminated_path(self):
        self.assertEqual('example.com/foo/*',
                         Annotation.guess_google_url("http://example.com/foo"))


class AnnotationsAlphaList(TestCase):

    def setUp(self):
        self.expected = [{'i': x, 'style': 'disabled'} for x in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789']

    def test_no_annotations_no_active_letter(self):
        results = Annotation.alpha_list()
        self.assertEqual(self.expected, results)

    def test_two_annotations_two_active_letters(self):
        f = Annotation.objects.create(comment="Fun with Python")
        five = Annotation.objects.create(comment="5 Python Anti-Patterns")
        results = Annotation.alpha_list()
        self.expected[5]['style'] = 'active'
        self.expected[-5]['style'] = 'active'
        self.assertEqual(self.expected, results)

    def test_two_annotations_two_active_letters_one_inactive_selected(self):
        f = Annotation.objects.create(comment="Fun with Python")
        five = Annotation.objects.create(comment="5 Python Anti-Patterns")
        results = Annotation.alpha_list(selection="B")
        self.expected[1]['style'] = 'selected'
        self.expected[5]['style'] = 'active'
        self.expected[-5]['style'] = 'active'
        self.assertEqual(self.expected, results)
