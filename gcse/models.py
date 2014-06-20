try:
    from urllib2 import urlopen
except ImportError:
    from urllib.request import urlopen

from string import ascii_letters

import xml.sax
import xml.sax.saxutils
import xml.sax.handler
from lxml import etree as ET

from django.db import models
from django.db import connection
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.core.validators import MaxValueValidator, MinValueValidator

from model_utils.models import TimeStampedModel

from .country_field import CountryField


class Label(models.Model):
    """Labels associated with an Annotation. Used to refine search results.
    https://developers.google.com/custom-search/docs/ranking#labels
    """
    name = models.CharField(max_length=128,
                            blank=False,
                            help_text=_('Google search refinement name.'))
    MODE_ELIMINATE = 'E'
    MODE_FILTER = 'F'
    MODE_BOOST = 'B'
    MODE_CHOICES = ((MODE_ELIMINATE, 'ELIMINATE'),
                    (MODE_FILTER, 'FILTER'),
                    (MODE_BOOST, 'BOOST'),
                    )
    # TODO SAS this need a migration for googility.com
    mode = models.CharField(
        verbose_name=_('status'),
        max_length=1,
        choices=MODE_CHOICES,
        default=MODE_FILTER,
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

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return "name: %s id: %s mode: %s weight: %s" % (self.name, self.id, self.mode, self.weight)

    @classmethod
    def get_mode(cls, mode_string):
        for mode_char, mode_str in cls.MODE_CHOICES:
            if mode_str == mode_string:
                return mode_char


class FacetItem(models.Model):
    """A named search refinement presented in the search results to CSE users."""
    title = models.CharField(max_length=128,
                             help_text=_('Refinement title displayed in search results.'))
    label = models.ForeignKey(Label,
                              null=True, # allow creation without Label
                              help_text=_('The label associated with this refinement facet.'))
    cse = models.ForeignKey('CustomSearchEngine',
                            help_text=_('The Custom Search Engine associated with this refinement facet.'))

    class Meta:
        ordering = ["title"]

    def __unicode__(self):
        return u'%s %s' % (self.title, self.label)


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
    file or URL using the XXXX and YYYY factory methods.

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
    using a separate file via the 'Include' XML element which invokes
    the XXXXX view.

    The Annotations selected are the intersection of Annotations whose
    Label.id fields join with the CSE.background_labels and
    CSE.faceitem_set.labels.

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
    title = models.CharField(max_length=128)
    description = models.CharField(max_length=256)
    input_xml = models.TextField(max_length=4096)
    output_xml = models.TextField(max_length=4096)

    background_labels = models.ManyToManyField(Label,
                                               related_name='cse_background_labels',
                                               help_text=_('Non-visible Labels for this search engine'))

    def facetitems_labels(self):
        """Return all the Labels for the FacetItems associated with this instance."""
        labels = Label.objects.raw('SELECT * FROM gcse_label INNER JOIN gcse_facetitem ON gcse_label.id = gcse_facetitem.label_id WHERE gcse_facetitem.cse_id = %s', [self.id])
        return labels

    def _create_or_update_xml_element(self, doc, name):
        value = getattr(self, name)
        if value:
            capitalize = name.capitalize()
            lower = name.lower()
            try:
                el = doc.xpath("/CustomSearchEngine/%s" % capitalize)[0]
            except IndexError:
                parent = doc.xpath("/CustomSearchEngine")[0]
                el = ET.XML("<%s></%s>" %(capitalize, capitalize))
                parent.insert(1, el)
            el.text = value
        
    def _update_xml(self):
        """Parse the input_xml and update it with the current database values in this instance."""
        doc = ET.fromstring(self.input_xml)
        self._create_or_update_xml_element(doc, "title")
        self._create_or_update_xml_element(doc, "description")
        # update Context's Facet and BackgroundLabels
        # for elem in rowset.getchildren():
        #     if int(elem.get("itemID")) not in idlist:
        #         rowset.remove(elem)
        
        # Add Include of Annotations
        self.output_xml = ET.tostring(doc, encoding='UTF-8', xml_declaration=True)

    @classmethod
    def instantiate_from_stream(stream):
        handler = CSESAXHandler()
        cse = handler.parseString(CSE_XML)
        cse._update_xml()
        cse.save()


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super(ActiveManager, self).get_queryset().\
            filter(status=AnnotationBase.STATUS_ACTIVE)


class AnnotationBase(TimeStampedModel):
    """
    Abstract base class upon which Annotation entries and local "Place"
    entries can be created.
    """
    comment = models.CharField(verbose_name=_('Business or Web Site Name'),
                               max_length=256,
                               blank=False,
                               help_text=_('Name/title of the site'))
    # allow blank for non-internet sites
    original_url = models.CharField(verbose_name=_('Web Site URL'),
                                    max_length=256,
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
                              validators=[MinValueValidator(-1),
                                          MaxValueValidator(1)],
                              help_text=_('Score value to influence label score - leave blank for default.'))
    # If the site uses supplied views for user moderated submissions:
    STATUS_SUBMITTED = 'S'
    STATUS_ACTIVE = 'A'
    STATUS_DELETED = 'D'
    STATUS_CHOICES = (
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_ACTIVE, _('Active')),
        (STATUS_DELETED, _('Deleted')),
    )
    status = models.CharField(verbose_name=_('status'),
                              max_length=1,
                              choices=STATUS_CHOICES,
                              default=STATUS_SUBMITTED)
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

    objects = models.Manager()
    active = ActiveManager()

    class Meta:
        abstract = True


class Annotation(AnnotationBase):
    """
    Concrete class representing an Annotation in the Google annotations file.
    https://developers.google.com/custom-search/docs/annotations
    """
    pass


class Place(AnnotationBase):
    """
    Concrete class representation of a physical place, organization, business
    that can be represented in an Annotation and/or on a Google map
    """
    # The labels and help text for these fields are defined in the forms.py
    address1 = models.CharField(verbose_name=_('Address Line 1'),
                                max_length=128,
                                blank=True)
    address2 = models.CharField(verbose_name=_('Address Line 2'),
                                max_length=128,
                                blank=True)
    city = models.CharField(verbose_name=_('City/Town'),
                            max_length=128,
                            blank=True)
    state = models.CharField(verbose_name=_('State/Province/Region'),
                             max_length=128,
                             blank=True)
    zipcode = models.CharField(verbose_name=_('Zip/Postal Code'),
                               max_length=128,
                               blank=True)
    country = CountryField(verbose_name=_('Country'),
                           max_length=2,
                           blank=True)
    phone = models.CharField(verbose_name=_('Telephone'),
                             max_length=128,
                             blank=True)
    email = models.EmailField(verbose_name=_('Business or Web Site Email'),
                              max_length=128,
                              blank=True)
    description = models.CharField(verbose_name=_('Description'),
                                   max_length=512,
                                   blank=True)

    # Fields not visible to end users
    submitter_email = models.EmailField(verbose_name=_('Submitter Email'),
                                        max_length=128,
                                        blank=True,
                                        help_text=_('Email address of the person who submitted this site information'))

    # Could use gis Point field but don't need that much functionality
    lat = models.DecimalField(verbose_name=_('Latitude'),
                              max_digits=10,
                              decimal_places=7,
                              null=True,
                              blank=True)
    lng = models.DecimalField(verbose_name=_('Longitude'),
                              max_digits=10,
                              decimal_places=7,
                              null=True,
                              blank=True)

    class Meta:
        ordering = ["about"]

    def __unicode__(self):
        return "%s %s" % (self.comment, self.id)

    def get_absolute_url(self):
        return ('gcse_annotation_detail', (), {'id': self.id})
    get_absolute_url = models.permalink(get_absolute_url)

    def wasAdded(self):
        return self.modified == self.created

    def shouldHaveAddress(self):
        """Does this annotation have Labels that indicate
        that it could have a physical address"""
        for label in self.labels.all():
            if label.physical:
                return True
        return False

    def hasAddress(self):
        return self.address1 and self.city and self.state and self.country

    def webOnly(self):
        for label in self.labels.all():
            if label.physical:
                return False
        return True

    def address(self):
        return " ".join([self.address1, self.city, self.state, self.country])

    @classmethod
    def alpha_list(cls, selection=None):
        """Return a list of the case insensitive matches of Annotation
        comment's first letters. For use in the view to give alpha based
        tabs for browsing"""
        cursor = connection.cursor()
        cursor.execute("SELECT distinct(substr(comment, 1, 1)) FROM "
                       "gcse_annotation order by substr(comment, 1, 1)")
        existent = [str(i[0]) for i in cursor.fetchall()]
        results = []
        for i in ascii_letters[26:] + "0123456789":
            style = ''
            if i == selection:
                style = "selected"
            elif i in existent:
                style = "active"
            results.append({'i': i, 'style': style})
        return results

    def labels_as_links(self):
        return "&nbsp;".join(
            ['<a href="%s?label=%s">%s</a>' % (
                reverse('browse_by_label'), l.name, l.name)
             for l in self.labels.all()]
            )


class CSESAXHandler(xml.sax.handler.ContentHandler):
    """Create and populate a CustomSearchEngine from an XML document."""

    def __init__(self):
        self.cse = None
        self.name = ''
        self.attrs = {}
        self.facet_item = None
        self.in_background_label = False

    def parseString(self, stream):
        xml.sax.parseString(stream, self)
        self.cse.input_xml = stream
        return self.cse

    def parse(self, url):
        xml.sax.parse(urlopen(url), self)
        return self.cse

    def startElement(self, name, attributes):
        self.name = name
        self.attrs[name] = ''
        if name == "CustomSearchEngine":
            self.cse, created = CustomSearchEngine.objects.\
                get_or_create(gid=attributes["id"])
        elif name == "FacetItem":
            title = attributes["title"]
            facet, created = FacetItem.objects.get_or_create(title=title,
                                                             cse=self.cse)
            self.cse.facetitem_set.add(facet)
            self.facet_item = facet
        elif name == 'BackgroundLabels':
            self.in_background_label = True
        elif name == "Label":
            # Try to find existing label
            lname = attributes['name']
            label, created = Label.objects.get_or_create(name=lname)
            # don't overwrite local label configurations
            if created:
                label.mode = Label.get_mode(attributes['mode'])
                if 'weight' in attributes:
                    label.weight = float(attributes['weight'])
                label.background = self.in_background_label
                label.save()
                if label.background:
                    self.cse.background_labels.add(label)
            if self.facet_item:
                self.facet_item.label = label
                self.facet_item.save()
                self.facet_item = None

    def characters(self, data):
        self.attrs[self.name] += data

    def endElement(self, name):
        if name == 'Title':
            self.cse.title = self.attrs[name]
        elif name == 'Description':
            self.cse.description = self.attrs[name]
        elif name == 'BackgroundLabels':
            self.in_background_label = False

class AnnotationSAXHandler(xml.sax.handler.ContentHandler):
    """Create a set of Annotation instances from an XML file."""

    def __init__(self):
        self.curAnnotation = None
        self.curLabel = None
        self.inComment = False
        self.annotations = []

    def parseString(self, stream):
        xml.sax.parseString(stream, self)

    def parse(self, url):
        xml.sax.parse(urlopen(url), self)

    def startElement(self, name, attributes):
        if name == "Annotation":
            self.curAnnotation, created = Annotation.objects.\
                get_or_create(about=attributes["about"])
        elif name == "AdditionalData":
            if attributes['attribute'] == 'original_url':
                original_url = attributes['value']
                # created some input data which had an asterisk at the end
                self.curAnnotation.original_url = original_url.rstrip("*")
        elif name == "Comment":
            self.inComment = True
            self.curAnnotation.comment = ''
        elif name == "Label":
            # Try to find existing label
            lname = attributes['name']
            label, created = Label.objects.get_or_create(name=lname)
            self.curAnnotation.labels.add(label)

    def characters(self, data):
        if self.inComment:
            self.curAnnotation.comment += data

    def endElement(self, name):
        if name == "Annotation":
            self.curAnnotation.save()
            self.annotations.append(self.curAnnotation)
            self.curAnnotations = None
        elif name == "Comment":
            self.inComment = False
            # Store in database unescaped - let view(s) escape if needed
            self.curAnnotation.comment = \
                xml.sax.saxutils.unescape(self.curAnnotation.comment)
