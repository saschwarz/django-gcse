from django.db import IntegrityError
from django.test import TestCase
from gcse.models import CustomSearchEngine, CSESAXHandler, Label

# Default CSE XML created by google
CSE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<CustomSearchEngine id="c12345-r678" keywords="" language="en" encoding="ISO-8859-1" domain="www.google.com" safesearch="true">
  <Title>AgilityNerd Site Search</Title>
  <Context>
    <BackgroundLabels>
      <Label name="_cse_c12345-r678" mode="FILTER" />
      <Label name="_cse_exclude_c12345-r678" mode="ELIMINATE" />
    </BackgroundLabels>
  </Context>
  <LookAndFeel code="2" resultsurl="http://agilitynerd.com/blog/googlesearch.index" adsposition="11" googlebranding="watermark" searchboxsize="31" resultswidth="500" element_layout="1" theme="1" custom_theme="true" text_font="Arial, sans-serif" url_length="full" element_branding="show" enable_cse_thumbnail="true" promotion_url_length="full" ads_layout="1">
    <Logo />
    <Colors url="#008000" background="#FFFFFF" border="#336699" title="#0000FF" text="#000000" visited="#663399" light="0000FF" logobg="336699" title_hover="#0000CC" title_active="#0000CC" />
    <Promotions title_color="#0000CC" title_visited_color="#0000CC" url_color="#008000" background_color="#FFFFFF" border_color="#336699" snippet_color="#000000" title_hover_color="#0000CC" title_active_color="#0000CC" />
    <SearchControls input_border_color="#D9D9D9" button_border_color="#666666" button_background_color="#CECECE" tab_border_color="#E9E9E9" tab_background_color="#E9E9E9" tab_selected_border_color="#FF9900" tab_selected_background_color="#FFFFFF" />
    <Results border_color="#FFFFFF" border_hover_color="#FFFFFF" background_color="#FFFFFF" background_hover_color="#FFFFFF" ads_background_color="#FDF6E5" ads_border_color="#FDF6E5" />
  </LookAndFeel>
  <AdSense>
    <Client id="partner-pub-id" />
  </AdSense>
  <EnterpriseAccount />
  <ImageSearchSettings enable="true" />
  <autocomplete_settings />
  <cse_advance_settings enable_speech="true" />
</CustomSearchEngine>
"""

# Semi customized
FACETED_XML = """
<GoogleCustomizations version="1.0">
<CustomSearchEngine id="csekeystring" version="1.0" volunteers="false" keywords="" visible="true" encoding="UTF-8" top_refinements="4">
  <Title>AgilityNerd Dog Agility Search</Title>
  <Description>Search for Dog Agility topics, clubs, trainers, facilities, organizations and stores</Description>
  <Context refinementsTitle="Refine results for $q:">
    <!-- max of FOUR Facets each with at most FOUR FacetItems -->
    <Facet>
      <FacetItem title="Blogs">
        <Label name="blogs" mode="BOOST" weight="0.8"/>
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
      <Label name="_cse_csekeystring" mode="FILTER" weight="1" />
      <Label name="_cse_exclude_csekeystring" mode="ELIMINATE" weight="1" />
    </BackgroundLabels>
  </Context>
  <LookAndFeel>
    <Logo url="http://data.agilitynerd.com/images/AgilityNerd_SideBySide.gif" destination="http://agilitynerd.com" height="51" />
  </LookAndFeel>
  <SubscribedLinks />
  <AdSense />
  <EnterpriseAccount />
</CustomSearchEngine>
<Include type="Annotations" href="http://googility.com/googility_annotations.xml"/>
</GoogleCustomizations>
"""

class TestCustomSearchEngine(TestCase):

    def test_adding_labels(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search',
                                 google_xml=CSE_XML,
                                 output_xml=CSE_XML
                                 )
        cse.save()
        l1 = Label(name="fred")
        l1.save()
        l1.mode = Label.MODE_FILTER
        l1.save()
        cse.labels.add(l1)
        l2 = Label(name="fred")
        l2.save()
        l2.mode = Label.MODE_ELIMINATE
        l2.save()
        cse.labels.add(l2)

        
class TestImportCustomSearchEngine(TestCase):

    def test_insert(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search',
                                 google_xml=CSE_XML,
                                 output_xml=CSE_XML
                                 )
        cse.save()

    def test_gid_is_unique(self):
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search',
                                 google_xml=CSE_XML,
                                 output_xml=CSE_XML
                                 )
        cse.save()
        cse = CustomSearchEngine(gid='c12345-r678',
                                 title='AgilityNerd Site Search',
                                 google_xml=CSE_XML,
                                 output_xml=CSE_XML
                                 )
        self.assertRaises(IntegrityError, cse.save)

    # def test_gid_populated_from_google_xml(self):
    #     cse = CustomSearchEngine(gid='c12345-r678',
    #                              title='Site Search',
    #                              google_xml=CSE_XML,
    #                              output_xml=CSE_XML
    #                              )
    #     cse.save()
    #     handler = CSESAXHandler()
    #     cse = handler.parseString(CSE_XML)


class TestCSESAXHandler(TestCase):

    def setUp(self):
        self.handler = CSESAXHandler()
        self.cse = self.handler.parseString(CSE_XML)

    def test_gid_is_parsed_from_xml(self):
        self.assertEqual('c12345-r678', self.cse.gid)

    def test_title_is_parsed_from_xml(self):
        self.assertEqual('AgilityNerd Site Search', self.cse.title)

    def test_labels_are_parsed_from_xml(self):
        cse = self.cse
        self.assertEqual(2, cse.labels.count())

        label_names = [x.name for x in cse.labels.all()]
        self.assertTrue("_cse_c12345-r678" in label_names)
        self.assertTrue("_cse_exclude_c12345-r678" in label_names)

        label_modes = [x.mode for x in cse.labels.all()]
        self.assertTrue(Label.MODE_FILTER in label_modes)
        self.assertTrue(Label.MODE_ELIMINATE in label_modes)

    def test_labels_are_parsed_from_facets_in_xml(self):
        self.cse = self.handler.parseString(FACETED_XML)
        cse = self.cse
        self.assertEqual(14, cse.labels.count())

        label_names = set([x.name for x in cse.labels.all()])
        self.assertEqual(label_names, set(["blogs", "club", "equipment", "forum", "general", "organization", "service", "store", "training", "facility", "video", "rental", "_cse_csekeystring", "_cse_exclude_csekeystring"]))

        label_modes = [x.mode for x in cse.labels.all()]
        self.assertTrue(Label.MODE_FILTER in label_modes)
        self.assertTrue(Label.MODE_ELIMINATE in label_modes)
        self.assertTrue(Label.MODE_BOOST in label_modes)

        self.assertEqual(1, cse.labels.filter(weight=0.8).count())
    def test_google_xml_is_parsed_from_xml(self):
        self.assertEqual(CSE_XML, self.cse.google_xml)

    def test_facet_items_are_parsed_from_xml(self):
        self.cse = self.handler.parseString(FACETED_XML)
        cse = self.cse
        self.assertEqual(12, cse.facet_items.count())
        
    # def test_output_xml_is_parsed_from_xml(self):
    #     self.assertEqual(CSE_XML, self.cse.output_xml)



class TestLabel(TestCase):

    def test_get_mode(self):
        self.assertEqual(Label.MODE_ELIMINATE, Label.get_mode("ELIMINATE"))
        self.assertEqual(Label.MODE_FILTER, Label.get_mode("FILTER"))
        self.assertEqual(Label.MODE_BOOST, Label.get_mode("BOOST"))
