# -*- coding: utf-8 -*-
"""
test_models
-----------

Tests for `django-gcse` model module.
"""
from lxml import etree as ET

from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from gcse.models import CustomSearchEngine, CSESAXHandler, Label, FacetItem

# Default CSE XML created by google
CSE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true">
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
</CustomSearchEngine>
"""

# Semi customized
FACETED_XML = """<?xml version=\'1.0\' encoding=\'UTF-8\'?>
<GoogleCustomizations version="1.0">
  <CustomSearchEngine id="csekeystring" version="1.0" volunteers="false" keywords="" visible="true" encoding="UTF-8" top_refinements="4">
    <Title>AgilityNerd Dog Agility Search</Title>
    <Description>Search for Dog Agility topics, clubs, trainers, facilities, organizations and stores</Description>
    <Context refinementsTitle="Refine results for $q:">
      <!-- max of FOUR Facets each with at most FOUR FacetItems -->
      <Facet>
        <FacetItem title="Blogs">
          <Label name="blogs" mode="BOOST"/>
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
</GoogleCustomizations>
"""


class TestCustomSearchEngine(TestCase):

    def test_adding_background_labels(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search'
                                 )
        cse.save()
        l1 = Label(name="keystring",
                   mode=Label.MODE_FILTER)
        l1.save()
        cse.background_labels.add(l1)

        l2 = Label(name="exclude_keystring",
                   mode=Label.MODE_ELIMINATE)
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

    def test_gid_populated_from_google_xml(self):
        cse = CustomSearchEngine.from_string(CSE_XML)
        self.assertEqual("c12345-r678", cse.gid)


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

    def setUp(self):
        Label.objects.all().delete()
        FacetItem.objects.all().delete()

    def test_input_matches_output_xml_when_no_changes_to_instance(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=CSE_XML)
        cse.save()
        cse._update_xml()
        self.assertEqual('', cse.title) # no title set so leave XML alone
        self.assertEqual("AgilityNerd Site Search", _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_title_when_title_is_changed(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 input_xml=CSE_XML)
        cse.save()
        cse._update_xml()
        self.assertEqual(cse.title, _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_title_element_when_there_is_no_title_element(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()
        cse._update_xml()
        self.assertEqual(cse.title, _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Title"))

    def test_output_xml_has_new_description_when_description_is_changed(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=CSE_XML)
        cse.save()
        cse._update_xml()
        self.assertEqual(cse.description, _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Description"))

    def test_output_xml_has_new_description_element_when_there_is_no_description_element(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()
        cse._update_xml()

        self.assertEqual(cse.description, _extractPathElementText(cse.output_xml, "/GoogleCustomizations/CustomSearchEngine/Description"))

    def test_output_xml_has_new_title_and_description_when_neither_exist(self):
        input_xml = """<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true"><Context/></CustomSearchEngine>"""
        cse = CustomSearchEngine(gid="c12345-r678",
                                 title="""Here's a new title in need of escaping: &<>""",
                                 description="""Here's a new description in need of escaping: &<>""",
                                 input_xml=input_xml)
        cse.save()
        cse._update_xml()

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
        cse._update_xml()

        self.assertEqual(1,
                         len(_extractPath(cse.output_xml,
                                          "/GoogleCustomizations/Include")))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.0.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include"))

    def test_output_xml_has_annotation_includes(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.save()
        cse.annotation_count = lambda: 2000
        cse._update_xml()

        self.assertEqual(2,
                         len(_extractPath(cse.output_xml,
                                          "/GoogleCustomizations/Include")))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.0.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include[1]"))
        self.assertEqual('<Include type="Annotations" href="//example.com/annotations/c12345-r678.1.xml"/>',
                         _extractPathAsString(cse.output_xml,
                                              "/GoogleCustomizations/Include[2]"))

    # def test_output_xml_has_same_facet_labels(self):
    #     cse = CustomSearchEngine.from_string(FACETED_XML)
    #     self.assertEqual(FACETED_XML, cse.output_xml)

    def test_output_xml_has_new_facet_labels(self):
        cse = CustomSearchEngine(gid="c12345-r678",
                                 input_xml=FACETED_XML)
        cse.save()
        label = Label(name="Dogs",
                      description="Dog refinement",
                      mode=Label.MODE_FILTER,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Dogs",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        label = Label(name="Cats",
                      description="Cat refinement",
                      mode=Label.MODE_FILTER,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Cats",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        cse._update_xml()
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
                      mode=Label.MODE_FILTER,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Dogs",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        label = Label(name="Cats",
                      description="Cat refinement",
                      mode=Label.MODE_FILTER,
                      weight=0.7)
        label.save()
        facet = FacetItem(title="Cats",
                          label=label,
                          cse=cse)
        facet.save()
        cse.facetitem_set.add(facet)
        cse._update_xml()
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
            cse._update_xml()

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
        self.cse = self.handler.parseString(CSE_XML)

    def test_gid_is_parsed_from_xml(self):
        self.assertEqual('c12345-r678', self.cse.gid)

    def test_title_is_parsed_from_xml(self):
        self.assertEqual('AgilityNerd Site Search', self.cse.title)

    def test_empty_description_is_parsed_from_xml(self):
        self.assertEqual('', self.cse.description)

    def test_description_is_parsed_from_xml(self):
        self.cse = self.handler.parseString(FACETED_XML)
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
        self.assertTrue(Label.MODE_FILTER in label_modes)
        self.assertTrue(Label.MODE_ELIMINATE in label_modes)
        self.assertTrue(Label.MODE_BOOST in label_modes)

        self.assertEqual(True, labels[0].background)
        self.assertEqual(True, labels[1].background)
        self.assertEqual(True, labels[2].background)

        self.assertEqual(None, labels[0].weight)
        self.assertEqual(None, labels[1].weight)
        self.assertEqual(0.8, labels[2].weight)

    def test_labels_are_parsed_from_facets_in_xml(self):
        self.cse = self.handler.parseString(FACETED_XML)
        cse = self.cse
        self.assertEqual(12, cse.facetitem_set.count())
        labels = cse.facetitems_labels()
        label_names = set([x.name for x in labels])
        self.assertEqual(set(["blogs", "club", "equipment", "forum", "general", "organization", "service", "store", "training", "facility", "video", "rental"]),
                         label_names)

        label_modes = [x.mode for x in labels]
        self.assertTrue(Label.MODE_FILTER in label_modes)
        self.assertFalse(Label.MODE_ELIMINATE in label_modes)
        self.assertTrue(Label.MODE_BOOST in label_modes)

        self.assertEqual(1, len([x for x in labels if x.weight==0.8]))

        self.assertEqual(set(["_cse_csekeystring", "_cse_exclude_csekeystring"]),
                         set([x.name for x in cse.background_labels.all()]))

    def test_input_xml_is_parsed_from_xml(self):
        self.assertEqual(CSE_XML, self.cse.input_xml)

    def test_facet_items_are_parsed_from_xml(self):
        self.cse = self.handler.parseString(FACETED_XML)
        cse = self.cse
        self.assertEqual(12, cse.facetitem_set.count())


class TestLabel(TestCase):

    def test_get_mode(self):
        self.assertEqual(Label.MODE_ELIMINATE, Label.get_mode("ELIMINATE"))
        self.assertEqual(Label.MODE_FILTER, Label.get_mode("FILTER"))
        self.assertEqual(Label.MODE_BOOST, Label.get_mode("BOOST"))

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
