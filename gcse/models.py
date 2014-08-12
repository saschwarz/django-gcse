# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from string import ascii_letters
import datetime
import math
from io import StringIO

from lxml import etree as ET
import lxml.sax
import xml.sax.saxutils
import xml.sax.handler

from django.db import models, connection
from django.db.models import Count, Q
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.encoding import python_2_unicode_compatible

from model_utils.models import TimeStampedModel
from model_utils import Choices
from model_utils.managers import InheritanceManager
from model_utils.managers import QueryManager

from ordered_model.models import OrderedModel

from .country_field import CountryField


settings.GCSE_CONFIG = dict({
        'NUM_FACET_ITEMS_PER_FACET': 4,
        'NUM_ANNOTATIONS_PER_FILE': 1000,
        'NUM_ANNOTATIONS_PER_PAGE': 25,
        'NUM_CSES_PER_PAGE': 25,
        'NUM_LABELS_PER_PAGE': 25,
        },
        **getattr(settings, 'GCSE_CONFIG' , {}))


@python_2_unicode_compatible
class Label(models.Model):
    """Labels associated with an Annotation. Used to refine search results.
    https://developers.google.com/custom-search/docs/ranking#labels
    """
    name = models.CharField(max_length=128,
                            blank=False,
                            help_text=_('Google search refinement name.'))
    MODE = Choices(('E', 'eliminate', 'ELIMINATE'),
                   ('F', 'filter', 'FILTER'),
                   ('B', 'boost', 'BOOST'))
    # TODO SAS this need a migration for googility.com
    mode = models.CharField(verbose_name=_('mode'),
                            max_length=1,
                            choices=MODE,
                            default=MODE.filter,
                            help_text=_('Controls whether an Annotation is promoted, demoted, or excluded'))
    # TODO SAS this need a migration for googility.com
    weight = models.FloatField(null=True, blank=True,
                               validators=[MinValueValidator(-1),
                                           MaxValueValidator(1)],
                               help_text=_('Score value to influence label score - leave blank for default.'))
    # These fields are used to control Label visibility if you use the
    # supplied optional views to display the Labels/Annotations.
    description = models.CharField(
        max_length=256,
        blank=False,
        null=False,
        help_text=_('Description shown to users adding/editing Annotations.'))
    # TODO SAS this needs to be migrated from googilit.com's "hidden" field to
    background = models.BooleanField(
        default=False,
        help_text=_('Show this label to end users? Set your Google feed Label(s) to hidden.'))
    # TODO SAS write a migration to move this field to Place for googility.com
    # physical = models.BooleanField(
    #     default=False,
    #     help_text=_('Annotations with this Label have a physical address.'))

    def cses(self):
        """
        All CustomSearchEngines having this Label as either a background label.
        or in a FacetItem.
        """
        cses = CustomSearchEngine.objects.filter(Q(background_labels=self) |
                                                 Q(facetitem__label=self)).distinct().order_by('title')
        return cses

    def annotations(self):
        """
        Annotations for this Label regardless of the CustomSearchEngine.
        """
        return Annotation.objects.filter(status=Annotation.STATUS.active,
                                         labels__name__exact=self.name)

    class Meta:
        ordering = ["name"]

    def get_absolute_url(self):
        return reverse('gcse_label_detail', kwargs={'id': self.id})

    @classmethod
    def get_mode(cls, mode_string):
        for mode_char, mode_str in cls.MODE:
            if mode_str == mode_string:
                return mode_char

    def xml(self, complete=True):
        weight = ''
        if self.weight and complete:
            weight = ' weight="%s"' % self.weight
        params = {"name": self.name,
                  "mode": self.get_mode_display(),
                  "weight": weight}
        return '<Label name="%(name)s" mode="%(mode)s"%(weight)s/>' % params

    def __str__(self):
        return "%d %s %s weight: %s" % (self.id, self.name, self.get_mode_display(), self.weight)


@python_2_unicode_compatible
class FacetItem(OrderedModel):
    """A named search refinement presented in the search results to CSE users."""
    title = models.CharField(max_length=128,
                             help_text=_('Refinement title displayed in search results.'))
    label = models.ForeignKey(Label,
                              null=True, # allow creation without Label
                              help_text=_('The label associated with this refinement facet.'))
    cse = models.ForeignKey('CustomSearchEngine',
                            help_text=_('The Custom Search Engine associated with this refinement facet.'))
    order_with_respect_to = 'cse'

    class Meta(OrderedModel.Meta):
        pass

    def xml(self):
        return '<FacetItem title="%s">%s</FacetItem>' % (self.title, self.label.xml(complete=False))

    def __str__(self):
        return '%s %s' % (self.title, self.label)


@python_2_unicode_compatible
class CustomSearchEngine(TimeStampedModel):
    """
    Hybrid representation of the Google Custom Search Engine
    'CustomSearchEngine' XML structure. The XML structure supplied to
    Google by the view is stored explicitly in the database with the
    most likely human editable elements replaced by the attributes
    stored in the database table. Those elements are replaced whenever
    the 'CustomSearchEngine' is edited and saved.

    The Google CustomSearchEngine XML format changes frequently and
    supporting the entire DTD in database tables just didn't seem
    worth the effort. The focus of this model is to allow adding,
    removing and editing Labels, Facets and Annotations. Editing other
    attributes/elements is done in the XML and the XML reimported, as
    described below.

    Instances can be created by importing the a CustomSearchEngine XML
    file or URL using the 'from_string' and 'from_url' factory methods.

    Alternately, the title and description fields should be populated
    and upon save the 'output_xml' is populated using the
    'gcse/output_xml.xml' template as a base with the same
    substitutions as performed when populated from an downloaded
    CustomSearchEngine file/URL.  That template can be overridden like
    any other application template for your needs.

    Once saved a CustomeSearchEngine instance can be updated by
    generating a new XML representation on the Google website and
    calling the factory methods with the 'merge=True' option or by
    manually updating the 'input_xml' field and 'save()'ing the
    instance.

    Once created FacetItems can be added to allow users to refine
    search results.

    The CSE generated by the default view supplies it's Annotations
    using separate file(s) via the 'Include' XML element which invokes
    the 'annotations' view.

    The Annotations selected are the Annotations whose Label.id fields
    join with the CSE.background_labels.

    Annotations have Labels associated with them and the CSE can
    define Labels that are filtered/excluded/boosted differently than
    the labels associated with the Annotations. Same thing with
    FacetItems that contain Labels - which are used by search engine
    users to filter/refine their searches.

    The factory methods allow you to share Labels across
    CustomSearchEngines or create new Labels with the same names. It
    all depends how you want to manage your Annotations: share them
    across multiple CSEs or not.
    """
    gid = models.CharField(max_length=32, unique=True)
    creator = models.CharField(max_length=32)
    title = models.CharField(max_length=128)
    description = models.CharField(max_length=256)
    input_xml = models.TextField(max_length=4096,
                                 blank=True)
    output_xml = models.TextField(max_length=4096,
                                  blank=True)

    background_labels = models.ManyToManyField(Label,
                                               related_name='background_cses',
                                               blank=True,
                                               help_text=_('Labels for this search engine'))

    DEFAULT_XML = b"""<?xml version="1.0"?>
    <CustomSearchEngine id="rdfdpnhicea" language="en" encoding="utf-8" enable_suggest="true">
      <Title>test</Title>
      <Context>
        <BackgroundLabels>
          <Label name="_cse_rdfdpnhicea" mode="FILTER" />
          <Label name="_cse_exclude_rdfdpnhicea" mode="ELIMINATE" />
        </BackgroundLabels>
      </Context>
      <LookAndFeel nonprofit="false" element_layout="8" theme="7" text_font="Arial, sans-serif" url_length="full" element_branding="show" enable_cse_thumbnail="true" promotion_url_length="full">
        <Logo />
        <Colors url="#008000" background="#FFFFFF" border="#FFFFFF" title="#0000CC" text="#000000" visited="#0000CC" title_hover="#0000CC" title_active="#0000CC" />
        <Promotions title_color="#0000CC" title_visited_color="#0000CC" url_color="#008000" background_color="#FFFFFF" border_color="#336699" snippet_color="#000000" title_hover_color="#0000CC" title_active_color="#0000CC" />
        <SearchControls input_border_color="#D9D9D9" button_border_color="#666666" button_background_color="#CECECE" tab_border_color="#E9E9E9" tab_background_color="#E9E9E9" tab_selected_border_color="#FF9900" tab_selected_background_color="#FFFFFF" />
        <Results border_color="#FFFFFF" border_hover_color="#FFFFFF" background_color="#FFFFFF" background_hover_color="#FFFFFF" ads_background_color="" ads_border_color="" />
      </LookAndFeel>
      <AdSense />
      <EnterpriseAccount />
      <ImageSearchSettings enable="false" />
      <autocomplete_settings />
      <sort_by_keys label="Relevance" key="" />
      <sort_by_keys label="Date" key="date" />
      <cse_advance_settings enable_speech="true" />
    </CustomSearchEngine>"""

    def annotations(self):
        return Annotation.objects.filter(status=Annotation.STATUS.active,
                                         labels__in=self.background_labels.all()).select_subclasses()

    def annotation_count(self, label_id=None):
        query = self.annotations()
        if label_id:
            return query.filter(labels__in=(label_id,)).count()
        return query.count()

    def all_labels(self):
        """Return all the Labels associated with this instance."""
        return Label.objects.filter(Q(facetitem__cse=self) |
                                    Q(background=True, background_cses=self)
                                    ).order_by('name')

    def facet_item_labels(self):
        """Return all the Labels for the FacetItems associated with this instance."""
        return Label.objects.filter(background=False, facetitem__cse=self).order_by('name')

    def facet_item_labels_counts(self):
        """Return all the Labels for the FacetItems associated with this instance and the counts of Annotations associated with them."""
        labels = self.facet_item_labels()
        annotations = Annotation.objects.filter(Q(labels__in=labels) | Q(labels__in=self.background_labels.all())).values('labels__id').order_by().annotate(Count('labels__id'))
        count_by_id = dict([(x['labels__id'], x['labels__id__count']) for x in annotations])
        label_counts = [(label, count_by_id.setdefault(label.id, 0)) for label in labels]
        return label_counts

    def get_absolute_url(self):
        return reverse('gcse_cse_detail', kwargs={'gid': self.gid})

    def _create_or_update_xml_element_text(self, doc, name):
        value = getattr(self, name)
        if value:
            capitalize = name.capitalize()
            lower = name.lower()
            el = doc.find(".//CustomSearchEngine/%s" % capitalize)
            if el is None:
                doc = doc.find(".//CustomSearchEngine")
                el = ET.XML("<%s/>" % capitalize)
                doc.insert(1, el)
            el.text = value

    def _update_background_labels(self, doc):
        """Replace the BackgroundLabel in the supplied doc's Context element."""
        context = doc.xpath(".//Context")[0]
        for child in context.getchildren():
            if child.tag == 'BackgroundLabels':
                context.remove(child)
        background = ET.XML("<BackgroundLabels />")
        context.insert(1, background)
        for label in self.background_labels.all():
            background.insert(1, ET.XML(label.xml()))

    def _update_facets(self, doc):
        """
        Add/replace the Facets in the supplied doc's Context element.
        TODO: maintain ordering of FacetItems
        """
        num_facet_items = settings.GCSE_CONFIG.get('NUM_FACET_ITEMS_PER_FACET')
        context = doc.xpath(".//Context")[0]
        for child in context.getchildren():
            if child.tag == 'Facet':
                context.remove(child)

        # Google limits to 16 facet items in groups of up to 4
        # but don't enforce overall limit just keep grouping them.
        for i, facet_item in enumerate(self.facetitem_set.all()):
            if i % num_facet_items == 0:
                facet_el = ET.XML("<Facet />")
                context.append(facet_el)
            facet_item_el = ET.XML(facet_item.xml())
            facet_el.append(facet_item_el)

    @classmethod
    def _add_google_customizations(cls, doc):
        if doc.tag != "GoogleCustomizations":
            root = ET.XML("<GoogleCustomizations />")
            root.insert(1, doc)
            doc = root
        return doc

    def _update_gid(self, doc):
        el = doc.xpath(".//CustomSearchEngine")[0]
        el.attrib['id'] = self.gid

    def update_output_xml_includes(self):
        doc = lxml.etree.fromstring(self.output_xml)
        if self._update_includes(doc, force_update=False):
            self.output_xml = ET.tostring(doc, encoding='UTF-8')
            return True
        return False

    def _update_includes(self, doc, force_update=True):
        existing = doc.findall(".//Include")
        num_annotations = self.annotation_count()
        per_file = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_FILE')
        # always at least one annotation file - even if empty
        num_files = max(1, int(math.ceil(num_annotations / per_file)))
        if not force_update and len(existing) == num_files:
            return False
        # remove existing include
        for el in existing:
            el.getparent().remove(el)
        # add an include for each index of Annotations
        for i in range(num_files):
            annotation_url = self._annotations_url(i)
            doc.append(ET.XML('<Include type="Annotations" href="%s"/>' % annotation_url))
        return True

    def _annotations_url(self, index):
        url = reverse('gcse_annotations', args=(self.gid, index))
        return  '//' + Site.objects.get_current().domain + url

    def _update_xml(self):
        """Parse the input_xml and update output_xml with the values in this instance."""
        input_xml = self.input_xml
        if not self.input_xml:
            # need to replace id attribute with id of this CSE
            input_xml = self.DEFAULT_XML
            self.input_xml = input_xml

        # since lxml doesn't trust encoding directives remove them
        doc = ET.fromstring(input_xml)
        # handle case where user gives us only CustomSearchEngine without
        # external Annotations file - wrap CSE with GoogleCustomizations element:
        doc = self._add_google_customizations(doc)
        self._update_gid(doc)
        self._create_or_update_xml_element_text(doc, "title")
        self._create_or_update_xml_element_text(doc, "description")

        # update Context's Facet and BackgroundLabels
        self._update_background_labels(doc)
        self._update_facets(doc)

        # Add Include of Annotations with link keyed on this CSE
        self._update_includes(doc)
        self.output_xml = ET.tostring(doc, encoding='UTF-8')

    def update(self):
        super(CustomSearchEngine, self).save()

    def save(self, *args, **kwargs):
        if not self.id:
            # need id so foreign key/m2m relations are satisfied
            # when inserting them inside _update_xml()
            super(CustomSearchEngine, self).save(*args, **kwargs)
        self._update_xml()
        # guaranteed to be an update now
        kwargs.update({'force_insert': False, 'force_update': True})
        super(CustomSearchEngine, self).save(*args, **kwargs)

    def __str__(self):
        return "%s" % (self.title,)

    @classmethod
    def from_string(cls, xml, import_linked_annotations=False):
        handler = CSESAXHandler()
        cse, linked_annotation_urls = handler.parseString(xml)
        cse.save()
        if import_linked_annotations:
            for url in linked_annotation_urls:
                Annotation.from_url(url)
        return cse

    @classmethod
    def from_url(cls, url, import_linked_annotations=False):
        handler = CSESAXHandler()
        cse, linked_annotation_urls = handler.parse(url)
        cse.save()
        if import_linked_annotations:
            for url in linked_annotation_urls:
                Annotation.from_url(url)
        return cse


class AnnotationManager(InheritanceManager):

    def active(self):
        return self.get_queryset().select_subclasses().filter(status=Annotation.STATUS.active)

    def submitted(self):
        return self.get_queryset().select_subclasses().filter(status=Annotation.STATUS.submitted)

    def deleted(self):
        return self.get_queryset().select_subclasses().filter(status=Annotation.STATUS.deleted)


@python_2_unicode_compatible
class Annotation(TimeStampedModel):
    """
    Abstract base class upon which Annotation entries and local "Place"
    entries can be created.
    """
    comment = models.CharField(verbose_name=_('Business or Web Site Name'),
                               max_length=256,
                               blank=False,
                               help_text=_('Name/title of the site'))
    # allow blank for non-internet sites
    original_url = models.URLField(verbose_name=_('Web Site URL'),
                                   blank=True,
                                   help_text=_('URL of the site'))
    # allow blank for non-internet sites
    about = models.CharField(verbose_name=_('Google Regexp'),
                             max_length=512,
                             blank=True,
                             help_text=_('Regular expression Google CSE uses to obtain pages for this site'))
    labels = models.ManyToManyField(Label,
                                    help_text=_('Labels visible to users of the search engine for this entry'))

    # TODO SAS Need googility migration for this field
    # https://developers.google.com/custom-search/docs/ranking#score
    score = models.FloatField(null=True, blank=True,
                              default=1,
                              validators=[MinValueValidator(-1),
                                          MaxValueValidator(1)],
                              help_text=_('Score value to influence label score - leave blank for default.'))
    # If the site uses supplied views for user moderated submissions:
    STATUS = Choices(('S', 'submitted', _('Submitted')),
                     ('A', 'active', _('Active')),
                     ('D', 'deleted', _('Deleted')))
    status = models.CharField(verbose_name=_('status'),
                              max_length=1,
                              choices=STATUS,
                              default=STATUS.submitted)
    # TODO SAS migration to remove this field
    # feed_label = models.ForeignKey(Label,
    #                                verbose_name=_('Feed Label'),
    #                                related_name='feed_label',
    #                                blank=True,
    #                                null=True,
    #                                help_text=_('The label used by Google to identify this feed')) # end users won't view/edit this setting; only admins.
    parent_version = models.ForeignKey('self',
                                       editable=False,
                                       blank=True,
                                       null=True,
                                       verbose_name=_('Parent Version'),
                                       related_name='newer_versions',
                                       help_text=_('Set to newer Annotation instance when user modifies this instance'))

    def cses(self):
        """
        All CustomSearchEngines having the same background_label(s) as this Annotation.
        """
        cses = CustomSearchEngine.objects.filter(background_labels__in=self.labels.all())
        return cses

    objects = AnnotationManager()

    @classmethod
    def from_string(cls, xml, klass=None):
        # allow use as Annotation subclass factory
        if klass is None:
            klass = cls
        handler = AnnotationSAXHandler(klass=klass)
        annotations = handler.parseString(xml)
        return annotations

    @classmethod
    def from_url(cls, url, klass=None):
        # allow use as Annotation subclass factory
        if klass is None:
            klass = cls
        handler = AnnotationSAXHandler(klass=klass)
        annotations = handler.parse(url)
        return annotations

    @classmethod
    def alpha_list(cls, selection=None, cse=None, label_id=None):
        """Return a list of the case insensitive matches of Annotation
        comment's first letters. For use in views to give alpha based
        links for browsing."""
        cursor = connection.cursor()
        if label_id is None:
            cursor.execute("SELECT DISTINCT(SUBSTR(comment, 1, 1)) FROM "
                           "gcse_annotation ORDER BY SUBSTR(comment, 1, 1)")
        else:
            cursor.execute("SELECT DISTINCT(SUBSTR(comment, 1, 1)) FROM "
                           "gcse_annotation JOIN gcse_annotation_labels ON gcse_annotation.id=gcse_annotation_labels.annotation_id WHERE label_id=%s"
"ORDER BY SUBSTR(comment, 1, 1)", (label_id,))
        existent = [i[0] for i in cursor.fetchall()]
        results = []
        for i in ascii_letters[26:] + "0123456789":
            style = ''
            if i == selection:
                style = "selected"
            elif i in existent:
                style = "active"
            else:
                style="disabled"
            results.append({'i': i, 'style': style})
        return results

    @classmethod
    def guess_google_url(cls, url):
        from django.utils.six.moves.urllib_parse import urlparse
        result = urlparse(url)

        # might be a single page
        path = result.hostname + result.path
        if not "." in result.path:
            if not result.path.endswith("/"):
                path += "/"
            path += "*"
        return path

    def labels_as_links(self, include_background_labels=True):
        return "".join(
            ['<a class="label-link" href="%s">%s</a>' % (
                reverse('gcse_label_detail', args=(l.id,)), l.name)
             for l in self.labels.order_by("name") if include_background_labels or not l.background]
            )

    def all_labels_as_links(self):
        return self.labels_as_links(include_background_labels=True)

    def facet_item_labels_as_links(self):
        return self.labels_as_links(include_background_labels=False)

    def get_absolute_url(self):
        return reverse('gcse_annotation_detail', kwargs={'id': self.id})

    def __str__(self):
        return "%s %s" % (self.comment, self.original_url)


# TODO Move to googility or new django app
#
# @python_2_unicode_compatible
# class Place(Annotation):
#     """
#     Concrete class representation of a physical place, organization, business
#     that can be represented in an Annotation and/or on a Google map
#     """
#     # The labels and help text for these fields are defined in the forms.py
#     address1 = models.CharField(verbose_name=_('Address Line 1'),
#                                 max_length=128,
#                                 blank=True)
#     address2 = models.CharField(verbose_name=_('Address Line 2'),
#                                 max_length=128,
#                                 blank=True)
#     city = models.CharField(verbose_name=_('City/Town'),
#                             max_length=128,
#                             blank=True)
#     state = models.CharField(verbose_name=_('State/Province/Region'),
#                              max_length=128,
#                              blank=True)
#     zipcode = models.CharField(verbose_name=_('Zip/Postal Code'),
#                                max_length=128,
#                                blank=True)
#     country = CountryField(verbose_name=_('Country'),
#                            max_length=2,
#                            blank=True)
#     phone = models.CharField(verbose_name=_('Telephone'),
#                              max_length=128,
#                              blank=True)
#     email = models.EmailField(verbose_name=_('Business or Web Site Email'),
#                               max_length=128,
#                               blank=True)
#     description = models.CharField(verbose_name=_('Description'),
#                                    max_length=512,
#                                    blank=True)

#     # Fields not visible to end users
#     submitter_email = models.EmailField(verbose_name=_('Submitter Email'),
#                                         max_length=128,
#                                         blank=True,
#                                         help_text=_('Email address of the person who submitted this site information'))

#     # Could use gis Point field but don't need that much functionality
#     lat = models.DecimalField(verbose_name=_('Latitude'),
#                               max_digits=10,
#                               decimal_places=7,
#                               null=True,
#                               blank=True)
#     lng = models.DecimalField(verbose_name=_('Longitude'),
#                               max_digits=10,
#                               decimal_places=7,
#                               null=True,
#                               blank=True)

#     class Meta:
#         ordering = ["about"]

#     def __str__(self):
#         return "%s %s" % (self.comment, self.id)

#     def get_absolute_url(self):
#         return reverse('gcse_annotation_detail', kwargs={'id': self.id})

#     def wasAdded(self):
#         return self.modified == self.created

#     def shouldHaveAddress(self):
#         """Does this annotation have Labels that indicate
#         that it could have a physical address"""
#         for label in self.labels.all():
#             if label.physical:
#                 return True
#         return False

#     def hasAddress(self):
#         return self.address1 and self.city and self.state and self.country

#     def webOnly(self):
#         for label in self.labels.all():
#             if label.physical:
#                 return False
#         return True

#     def address(self):
#         return " ".join([self.address1, self.city, self.state, self.country])


class CSESAXHandler(xml.sax.handler.ContentHandler):
    """Create and populate a CustomSearchEngine from an XML document."""

    def __init__(self):
        self.cse = None
        self.name = ''
        self.attrs = {}
        self.facet_index = 0
        self.facet_item = None
        self.in_background_label = False
        self.linked_annotation_urls = []

    def _parse(self, tree):
        lxml.sax.saxify(tree, self)
        self.cse.input_xml = lxml.etree.tostring(tree)
        return self.cse, self.linked_annotation_urls

    def parseString(self, xml):
        tree = lxml.etree.fromstring(xml)
        return self._parse(tree)

    def parse(self, url):
        tree = lxml.etree.parse(url)
        return self._parse(tree)

    def startElementNS(self, ns_name, qname, attributes):
        uri, name = ns_name
        self.name = name
        self.attrs[name] = ''
        if name == "CustomSearchEngine":
            self.cse, created = CustomSearchEngine.objects.\
                get_or_create(gid=attributes[(None, "id")])
        elif name == "FacetItem":
            title = attributes[(None, "title")]
            facet, created = FacetItem.objects.get_or_create(title=title,
                                                             cse=self.cse)
            facet.order = self.facet_index
            facet.save()
            self.facet_index += 1
            self.cse.facetitem_set.add(facet)
            self.facet_item = facet
        elif name == 'BackgroundLabels':
            self.in_background_label = True
        elif name == "Label":
            # Try to find existing label
            lname = attributes[(None, 'name')]
            label, created = Label.objects.get_or_create(name=lname)
            # don't overwrite local label configurations
            if created:
                label.mode = Label.get_mode(attributes[(None, 'mode')])
                if (None, 'weight') in attributes:
                    label.weight = float(attributes[(None, 'weight')])
                label.background = self.in_background_label
                label.save()
                if label.background:
                    self.cse.background_labels.add(label)
            if self.facet_item:
                self.facet_item.label = label
                self.facet_item.save()
                self.facet_item = None
        elif name == 'Include':
            url = attributes.get((None, 'href'))
            if url:
                self.linked_annotation_urls.append(url)

    def characters(self, data):
        self.attrs[self.name] += data

    def endElementNS(self, ns_name, qname):
        uri, name = ns_name
        if name == 'Title':
            self.cse.title = self.attrs[name]
        elif name == 'Description':
            self.cse.description = self.attrs[name]
        elif name == 'BackgroundLabels':
            self.in_background_label = False


class AnnotationSAXHandler(xml.sax.handler.ContentHandler):
    """
    Create a set of Annotation instances from an XML file.  Finds or
    creates related Labels by name, score and timestamp - doesn't keep
    them unique to a specific CustomSearchEngine.

    Uniqueness could be implemented by passing a CSE's Label(s) into
    this handler and adding only those Label instances to each
    Annotation. If not in the supplied Labels then the db would be
    searched for Label's with those names. If more than one is found
    raise an assertion?, add them all?
    """

    def __init__(self, klass=Annotation):
        self.klass = klass
        self.curAnnotation = None
        self.curLabel = None
        self.inComment = False
        self.annotations = []

    def _parse(self, tree):
        lxml.sax.saxify(tree, self)

    def parseString(self, xml):
        tree = lxml.etree.fromstring(xml)
        self._parse(tree)
        return self.annotations

    def parse(self, url):
        tree = lxml.etree.parse(url)
        self._parse(tree)
        return self.annotations

    def _convert_google_timestamp(self, tstring):
        if tstring:
            adate = datetime.datetime.fromtimestamp(int(tstring, 16)/1000000)
        else:
            adate= datetime.datetime.now()
        return timezone.make_aware(adate, timezone.get_current_timezone())

    def startElementNS(self, ns_name, qname, attributes):
        uri, name = ns_name
        if name == "Annotation":
            self.curAnnotation, created = self.klass.objects.\
                get_or_create(about=attributes[(None, "about")],
                              score=attributes.get((None, "score")),
                              created=self._convert_google_timestamp(attributes.get((None, "timestamp"))))
            # imports are always active
            self.curAnnotation.status = Annotation.STATUS.active
        elif name == "AdditionalData":
            if attributes[(None, 'attribute')] == 'original_url':
                original_url = attributes[(None, 'value')]
                # created some input data which had an asterisk at the end
                self.curAnnotation.original_url = original_url.rstrip("*")
        elif name == "Comment":
            self.inComment = True
            self.curAnnotation.comment = ''
        elif name == "Label":
            # Try to find existing label
            lname = attributes[(None, 'name')]
            label, created = Label.objects.get_or_create(name=lname)
            self.curAnnotation.labels.add(label)

    def characters(self, data):
        if self.inComment:
            self.curAnnotation.comment += data

    def endElementNS(self, ns_name, qname):
        if qname == "Annotation":
            self.curAnnotation.save()
            self.annotations.append(self.curAnnotation)
            self.curAnnotation = None
        elif qname == "Comment":
            self.inComment = False
            # Store in database unescaped - let view(s) escape if needed
            self.curAnnotation.comment = \
                xml.sax.saxutils.unescape(self.curAnnotation.comment)

# TODO:
# - reloading same GCSE XML file to optionally create new what(?).
# - delete old FacetItems and their Labels on import (with flag?) if unused by any Annotation.
# - slugify label, annotation, and GCSE
