import datetime
from urllib2 import urlopen
from string import ascii_letters

import xml.sax
import xml.sax.saxutils
import xml.sax.handler

from django.db import models
from django.db import connection
from django.utils.translation import ugettext as _
from django.conf import settings
from django.core.urlresolvers import reverse

from country_field import CountryField


settings.GCSE_LABEL_NAMES = getattr(settings, 'GCSE_LABEL_NAMES', [])


class Label(models.Model):
    """Labels associated with an Annotation. Used to refine search results"""
    name = models.CharField(max_length=128, blank=False, help_text=_('Google search refinement name.'))
    description = models.CharField(max_length=256, blank=False, null=False, help_text=_('Description shown to users adding/editing sites.'))
    hidden = models.BooleanField(default=False, help_text=_('Show this label to end users? Set your Google feed label to hidden.'))
    physical = models.BooleanField(default=False, help_text=_('An Annotation associated with this Label would have a physical address.'))
    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Annotation(models.Model):
    """A single Annotation entry"""
    comment = models.CharField(verbose_name=_('Business or Web Site Name'), max_length=256, blank=False, help_text=_('Name/title of the site'))
    # allow as null for non-internet sites
    original_url = models.CharField(_('Web Site URL'), max_length=256, blank=True, help_text=_('URL of the site'))
#    original_url = models.URLField(_('Web Site URL'), max_length=256, blank=True, help_text=_('URL of the site'))
    # allow as null for non-internet sites
    about = models.CharField(verbose_name=_('Google Regexp'), max_length=512, blank=True, help_text=_('Regular expression Google CSE uses to obtain pages for this site'))
    labels = models.ManyToManyField(Label, help_text=_('Labels visible to users of the search engine for this entry'))
    created = models.DateTimeField(verbose_name=_('Created'), default=datetime.datetime.now, help_text=_('Date and time this entry was created'), editable=False)
    modified = models.DateTimeField(verbose_name=_('Last Modified'), default=datetime.datetime.now, help_text=_('Date and time this entry was last modified'), editable=False)
    # The labels and help text for these fields are defined in the forms.py
    address1 = models.CharField(verbose_name=_('Address Line 1'), max_length=128, blank=True)
    address2 = models.CharField(_('Address Line 2'), max_length=128, blank=True)
    city = models.CharField(_('City/Town'), max_length=128, blank=True)
    state = models.CharField(_('State/Province/Region'), max_length=128, blank=True)
    zipcode = models.CharField(_('Zip/Postal Code'), max_length=128, blank=True)
    country = CountryField(_('Country'), max_length=2, blank=True)
    phone = models.CharField(_('Telephone'), max_length=128, blank=True)
    email = models.EmailField(_('Business or Web Site Email'), max_length=128, blank=True)
    description = models.CharField(_('Description'),  max_length=512, blank=True)

    # Fields not visible to end users
    submitter_email = models.EmailField(verbose_name=_('Submitter Email'), max_length=128, blank=True, help_text=_('Email address of the person who submitted this site information'))
    feed_label = models.ForeignKey(Label, verbose_name=_('Feed Label'), related_name='feed_label', blank=True, null=True, help_text=_('The label used by Google to identify this feed')) # end users won't view/edit this setting; only admins.
    STATUS_CHOICES = (
        ('S', 'Submitted'),
        ('A', 'Active'),
        ('D', 'Deleted'),
    )
    status = models.CharField(verbose_name=_('status'), max_length=1, choices=STATUS_CHOICES, default='A')
    parent_version = models.ForeignKey('self', editable=False, blank=True, null=True, verbose_name=_('Parent Version'), related_name='newer_versions', help_text=_('Set to newer Annotation instance when user modifies this instance'))

    # Could use gis Point field but don't need that much functionality
    lat = models.DecimalField(verbose_name=_('Latitude'), max_digits=10, decimal_places=7, null=True, blank=True) # Enough precision for Google Maps
    lng = models.DecimalField(verbose_name=_('Longitude'), max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        ordering = ["about"]

    def __unicode__(self):
        return "%s %s" %(self.comment, self.id)

    def get_absolute_url(self):
        return ('cse_annotation_detail', (), {'id': self.id})
    get_absolute_url = models.permalink(get_absolute_url)

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        now = datetime.datetime.now()
        if not self.id:
            self.created = now
        self.modified = now
        super(Annotation, self).save(force_insert, force_update, *args, **kwargs)

    def wasAdded(self):
        return self.modified == self.created

    def shouldHaveAddress(self):
        """Does this annotation have labels that indicate that it could have a physical address"""
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
        """Return a list of the case insensitive matches of Annotation comment's first letters.
        For use in the view to give alpha based tabs for browsing"""
        cursor = connection.cursor()
        cursor.execute("SELECT distinct(substr(comment, 1, 1)) FROM cse_annotation order by substr(comment, 1, 1)")
        existent = [str(i[0]) for i in cursor.fetchall()]
        results = []
        for i in ascii_letters[26:] + "0123456789":
            style = ''
            if i == selection:
                style = "selected"
            elif i in existent:
                style = "active"
            results.append({'i': i, 'style':style})
        return results

    def labels_as_links(self):
        return "&nbsp;".join(['<a href="%s?label=%s">%s</a>' % (reverse('browse_by_label'), l.name, l.name) for l in self.labels.all()])

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
        # print "startElement", name
        if name == "Annotation":
            self.curAnnotation, found = Annotation.objects.get_or_create(about=attributes["about"])
            # print self.curAnnotation, found
        elif name == "AdditionalData":
            # print name, attributes
            if attributes['attribute'] == 'original_url':
                original_url = attributes['value']
                # found some input data which had an asterisk at the end
                self.curAnnotation.original_url = original_url.rstrip("*")
                # print self.curAnnotation
        elif name == "Comment":
            self.inComment = True
            self.curAnnotation.comment = ''
        elif name == "Label":
            # Try to find existing label
            label, found = Label.objects.get_or_create(name=attributes['name'])
            # print label, found
            if label.name in GCSE_LABEL_NAMES:
                self.curAnnotation.feed_label = label
            else:
                self.curAnnotation.labels.add(label)

    def characters(self, data):
        if self.inComment:
            self.curAnnotation.comment += data

    def endElement(self, name):
        if name == "Annotation":
            # print self.curAnnotation
            self.curAnnotation.save()
            self.annotations.append(self.curAnnotation)
            # print "ANNOTATIONS", self.annotations
            self.curAnnotations = None
        elif name == "Comment":
            self.inComment = False
            # Store in database unescaped - let view(s) escape if needed
            self.curAnnotation.comment = xml.sax.saxutils.unescape(self.curAnnotation.comment)
