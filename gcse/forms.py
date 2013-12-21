from itertools import chain
from django import forms
from django.forms import ModelForm
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_unicode
from models import Annotation, Label
from model_fields import get_labels_for


class ImportForm(forms.Form):
    """Import a local or remote (via HTTP) annotation file. Available to admin users."""
    fileName = forms.FileField(label=_("File name"), required=False)
    url = forms.URLField(label=_("URL"), required=False, widget=forms.TextInput(attrs={'size':100}))

class SpecialMultipleChoiceField(forms.MultipleChoiceField):
    """Allows choices list elements to have a third ignored value"""
    def valid_value(self, value):
        "Check to see if the provided value is a valid choice"
        for k, v, ignore in self.choices:
            if type(v) in (tuple, list):
                # This is an optgroup, so look inside the group for options
                for k2, v2 in v:
                    if value == smart_unicode(k2):
                        return True
            else:
                if value == smart_unicode(k):
                    return True
        return False

class SpecialCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    """Accepts a third 'help' choice list element to be displayed below the label and checkbox"""
    def render(self, name, value, attrs=None, choices=()):
        if value is None: value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<ul>']
        # Normalize to strings
        str_values = set([force_unicode(v) for v in value])
        for i, (option_value, option_label, option_help) in enumerate(chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
                label_for = u' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_unicode(option_value)
            option_help = force_unicode(option_help)
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(force_unicode(option_label))
            output.append(u'''<li><label%s>%s %s</label><br/><span class="help">%s</span></li>''' % (label_for, rendered_cb, option_label.capitalize(), option_help))
        output.append(u'</ul>')
        return mark_safe(u'\n'.join(output))

class AnnotationForm(ModelForm):
    """End user form for modifying or adding new sites to the index."""
    class Meta:
        model = Annotation
        exclude = ('about', 'created', 'newer_version', 'modified', 'status',)

    labels_dict = get_labels_for(Annotation, cap=False)
    comment = forms.CharField(label=labels_dict['comment'], widget=forms.TextInput(attrs={'size':'50'}))
    original_url = forms.CharField(label=labels_dict['original_url'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
#    original_url = forms.URLField(label=labels_dict['original_url'], widget=forms.TextInput(attrs={'size':'50'}), required=False, error_messages={'invalid': _(u'Please enter a valid URL: http://example.com')}) # initial="http://" - requires that URLField be subclassed and a custom clean() be written
    submitter_email = forms.EmailField(label=labels_dict['submitter_email'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    address1 = forms.CharField(label=labels_dict['address1'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    address2 = forms.CharField(label=labels_dict['address2'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    city = forms.CharField(label=labels_dict['city'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    state = forms.CharField(label=labels_dict['state'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    zipcode = forms.CharField(label=labels_dict['zipcode'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    phone = forms.CharField(label=labels_dict['phone'], widget=forms.TextInput(attrs={'size':'50'}), required=False)
    email = forms.EmailField(label=labels_dict['email'],
                             help_text=_('Email address of business/site. Will be spam protected.'),
                             widget=forms.TextInput(attrs={'size':'50'}), required=False)
    description = forms.CharField(label=labels_dict['description'], widget=forms.Textarea(attrs={'cols':'70', 'rows':'8'}), required=False)

    def __init__(self, *args, **kwargs):
        super(AnnotationForm, self ).__init__( *args, **kwargs )
        # Show the latest non-hidden labels to the user for their selection
        self.fields['labels'] = SpecialMultipleChoiceField(widget=SpecialCheckboxSelectMultiple,
                                                           choices=[(o.id, str(o), o.description) for o in Label.objects.filter(hidden=False).order_by('name')])
