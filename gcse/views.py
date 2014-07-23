from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import never_cache
from django.views.generic.base import View
from django.views.generic import (DetailView, ListView, TemplateView)
from django.core.mail import mail_managers
from django.core import urlresolvers
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from gcse.models import CustomSearchEngine, Annotation, Label
from gcse.forms import PlaceForm
from .model_fields import get_labels_for
#from recaptcha.client import captcha

try:
    from django.utils import simplejson as json
except ImportError:
    import json


class CustomSearchEngineList(ListView):
    """
    Generate list of all CustomSearchEngines.
    """
    context_object_name = 'gcse_list'
    model = CustomSearchEngine
    paginate_by = settings.GCSE_CONFIG.get('NUM_CSES_PER_PAGE')
    template_name = 'gcse/cse_list.html'


class CustomSearchEngineDetail(DetailView):
    model = CustomSearchEngine
    slug_url_kwarg = 'gid'
    slug_field = 'gid'
    template_name = 'gcse/cse_detail.html'


class CustomSearchEngineDetailXML(View):
    """
    Generate CustomSearchEngine XML with updated Annotation Include elements.
    """
    def get(self, request, *args, **kwargs):
        cse = get_object_or_404(CustomSearchEngine,
                                gid=kwargs['gid'])
        if cse.update_output_xml_includes():
            cse.update()
        return HttpResponse(cse.output_xml)


class CSEAnnotations(ListView):
    """
    Generate paginated Annotation XML for a specified CustomSearchEngine.
    """
    context_object_name = 'annotations'
    model = CustomSearchEngine
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_FILE')
    slug_url_kwarg = 'gid'
    template_name = 'gcse/annotation.xml'

    def get_queryset(self):
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        return cse.annotations()


class CSEAnnotationList(ListView):
    """
    Render all the Annotations in alphabetical order in a paged manner for a single CSE.
    """
    context_object_name = 'annotation_list'
    model = Annotation
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_PAGE')
    template_name = 'gcse/cse_annotation_list.html'

    def get_queryset(self):
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        self.cse = cse
        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query)
            )
        return cse.annotations().filter(qset).order_by('comment')

    def get_context_data(self, *args, **kwargs):
        context = super(CSEAnnotationList, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['index'] = Annotation.alpha_list(query)
        context['query'] = query
        context['count'] = self.cse.annotation_count()
        context['cse'] = self.cse
        return context


class AnnotationList(ListView):
    """
    Render all the Annotations in alphabetical order in a paged manner.
    """
    context_object_name = 'annotation_list'
    model = Annotation
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_PAGE')
    template_name = 'gcse/annotation_list.html'

    def get_queryset(self):
        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query)
            )
        return Annotation.objects.active().filter(qset).distinct().order_by('comment')

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationList, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['index'] = Annotation.alpha_list(query)
        context['query'] = query
        context['count'] = Annotation.objects.count()
        return context


class AnnotationDetail(DetailView):
    pass


class LabelList(ListView):
    """
    Render all the Labels in alphabetical order in a paged manner.
    """
    model = Label
    paginate_by = settings.GCSE_CONFIG.get('NUM_LABELS_PER_PAGE')
    template_name = 'gcse/label_list.html'


class CSELabelList(ListView):
    """
    Render all the Labels for a Custom Search Engine in alphabetical order in a paged manner.
    """
    model = Label
    paginate_by = settings.GCSE_CONFIG.get('NUM_LABELS_PER_PAGE')
    template_name = 'gcse/cse_label_list.html'


class LabelDetail(DetailView):

    model = Label
    slug_url_kwarg = 'id'
    slug_field = 'id'


class CSELabelDetail(ListView):
    """
    Show the Annotations for a Label in a specific CustomSearchEngine.
    """
    model = Label
    context_object_name = 'annotations'
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_PAGE')
    slug_url_kwarg = 'id'
    slug_field = 'id'
    template_name = 'gcse/label_detail.html'

    def get_queryset(self):
        label = get_object_or_404(Label,
                                  pk=self.kwargs['id'])
        self.label = label
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        self.cse = cse
        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query) &
            Q(labels__in=[label])
            )
        return cse.annotations().filter(qset).order_by('comment')

    def get_context_data(self, *args, **kwargs):
        context = super(CSELabelDetail, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['label'] = self.label
        context['index'] = Annotation.alpha_list(query) # TODO filter by CSE
        context['query'] = query
        context['count'] = self.cse.annotation_count() # TODO filter by query
        context['cse'] = self.cse
        return context

def index(request, num_annotations=5, template='index.html'):
    """Render main page with lists of recently created and recently modified Annotations"""
    active = Annotation.active
    return render_to_response(template,
                              {
            'created': active.exclude(comment='').order_by('-created')[:num_annotations],
            'modified': active.exclude(comment='').extra(where=['gcse_annotation.modified != gcse_annotation.created']).order_by('-modified')[:num_annotations],
            },
                              context_instance=RequestContext(request)
                              )


def search(request, num=20, template="gcse/search.html"):
    query = request.GET.get('q', '')
    if query:
        qset = (
            Q(original_url__icontains=query) |
            Q(comment__icontains=query)
        )
        paginator = Paginator(Annotation.active.filter(qset).distinct().order_by('comment'), num)
    else:
        paginator = Paginator([], num)

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        results = paginator.page(page)
    except (EmptyPage, InvalidPage):
        results = paginator.page(paginator.num_pages)

    return render_to_response(template,
                              {"results": results,
                               "query": query
                               },
                              context_instance=RequestContext(request))


def view(request, id, template='gcse/view.html'):
    """Display an end user read only view of the site information"""
    site = get_object_or_404(Annotation, pk=id)
    return render_to_response(template,
                              {'site': site,
                               'labels': get_labels_for(site, cap=None),
                               },
                              context_instance=RequestContext(request))


def directions(request, id):
    """Display an end user read only view of the site information with a Google map for getting directions"""
    site = get_object_or_404(Annotation, pk=id)
    return render_to_response('gcse/directions.html',
                              {'site': site,
                               'labels': get_labels_for(site, cap=None)
                               },
                              context_instance=RequestContext(request))


def _all_labels_to_bitmasks(all_labels):
    """Given a list of Labels return a dict mapping the label names to a bitmask"""
    l_dict = {}
    for i, label in enumerate(all_labels):
        l_dict[label.name] = 1<<i
    return l_dict


def _labels_to_mask(labels, label_to_bitmask_map):
    """Given a list of Labels return a number that is the 'or' of them into an integer"""
    value = 0
    for label in labels:
        value |= label_to_bitmask_map[label.name]
    return value


def map(request, template='gcse/map.html'):
    """Display map with local search capability"""
    # Get all sites with lat and lng set so they can be mapped w/o
    startaddress = request.GET.get("startaddress", '')
    sites = Annotation.active.exclude(lat=None).exclude(lng=None)
    label_bitmasks = _all_labels_to_bitmasks(Label.objects.filter(hidden=False).order_by('name'))
    for site in sites:
        site.label_value = _labels_to_mask(site.labels.all(), label_bitmasks)
    return render_to_response(template,
                              {'sites': sites,
                               'labels': label_bitmasks,
                               'startaddress': startaddress,
                               'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY},
                              context_instance=RequestContext(request))


def edit_update_email(object):
    """
    Send email to managers when a change to an Annotation/Place has been
    submitted by an end user.
    """
    admin_url = urlresolvers.reverse('admin:gcse_annotation_change',
                                     args=(object.id,))
    email_body = _("Annotation added/edited: http://%s%s admin: http://%s%s") % (
        Site.objects.get_current().domain,
        object.get_absolute_url(),
        Site.objects.get_current().domain,
        admin_url)
    mail_managers(_("Annotation Added/Edited"), email_body)


def edit(request, id=None, add=False, template='gcse/edit.html'):
    """Edit an existing Annotation or create a new one.
    Modification and creations via this mechanism are not
    immediately visible to the end user."""
    # Initialize to an empty string, not None, so the reCAPTCHA call query string
    # will be correct if there wasn't a captcha error on POST.
    captcha_error = ""
    a = None
    if request.method == 'POST':
# SAS FIX!
        # Check the form captcha.  If not good, pass the template an error code
        # captcha_response = \
        # captcha.submit(request.POST.get("recaptcha_challenge_field", None),
        #                request.POST.get("recaptcha_response_field", None),
        #                settings.RECAPTCHA_PRIVATE_KEY,
        #                request.META.get("REMOTE_ADDR", None))
        # if not captcha_response.is_valid:
        #     captcha_error = "&error=%s" % captcha_response.error_code
        if id: # update existing entry
            instance = Annotation.objects.get(pk=id)
            # replace database instance's values with form's values
            form = PlaceForm(data=request.POST, instance=instance)
            if captcha_error is '' and form.is_valid():
                newInstance = form.save(commit=False)
                if newInstance.state != 'nonn':
                    # allow hackers to think they succeeded
                    newInstance.id = None  # get a new id on save
                    newInstance.status = 'S'  # save disabled
                    newInstance.save()
                    form.save_m2m()
                    # make the new instance point to the permanent instance
                    instance = Annotation.objects.get(pk=id)
                    newInstance.parent_version = instance
                    newInstance.save()
                    edit_update_email(newInstance)
                return HttpResponseRedirect(reverse('gcse_thanks'))
        else:  # new entry
            form = PlaceForm(request.POST)
            if captcha_error is '' and form.is_valid():
                instance = form.save(commit=False)
                instance.status = 'S'
                instance.save()
                form.save_m2m()
                edit_update_email(instance)
                return HttpResponseRedirect(reverse('gcse_thanks'))
    else:
        if id:
            a = get_object_or_404(Annotation, pk=id)
            form = PlaceForm(instance=a)
        else:
            form = PlaceForm()
    email = a and a.email != '' and a.email or ''
    return render_to_response(template,
                              {'form': form,
                               'add': add,
                               'email': email,
                               'original_url': a and a.original_url or ""},
                              context_instance=RequestContext(request))


def results(request, template='gcse/results.html'):
    """Render CSE results"""
    return render_to_response(template,
                              context_instance=RequestContext(request))
