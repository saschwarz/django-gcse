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


class CustomSearchEngineResults(CustomSearchEngineDetail):
    template_name = 'gcse/cse_results.html'


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
        return Annotation.objects.active().filter(qset).distinct().order_by('comment') #.prefetch_related('labels')

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationList, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['index'] = Annotation.alpha_list(selection=query)
        context['query'] = query
        context['count'] = Annotation.objects.count()
        return context


class AnnotationSearchList(ListView):
    """
    Render all the matching Annotations the query string.
    """
    model = Annotation
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_PAGE')
    template_name = 'gcse/search.html'

    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            qset = (
                Q(original_url__icontains=query) |
                Q(comment__icontains=query)
                )
            return Annotation.objects.active().filter(qset).distinct().order_by('comment') #.prefetch_related('labels')
        else:
            return []

    def get_context_data(self, *args, **kwargs):
        context = super(AnnotationSearchList, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        context['query'] = query
        return context


class CSEAnnotationList(AnnotationList):
    """
    Render all the Annotations in alphabetical order in a paged manner for a single CSE.
    """
    template_name = 'gcse/cse_annotation_list.html'

    def get_queryset(self):
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        self.cse = cse
        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query)
            )
        return cse.annotations().filter(qset).order_by('comment').prefetch_related('labels')

    def get_context_data(self, *args, **kwargs):
        context = super(CSEAnnotationList, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['index'] = Annotation.alpha_list(selection=query)
        context['query'] = query
        context['count'] = self.cse.annotation_count()
        context['cse'] = self.cse
        return context


class AnnotationDetail(DetailView):
    model = Annotation
    slug_url_kwarg = 'id'
    slug_field = 'id'
    template_name = 'gcse/annotation_detail.html'


class LabelList(ListView):
    """
    Render all the Labels in alphabetical order in a paged manner.
    """
    model = Label
    paginate_by = settings.GCSE_CONFIG.get('NUM_LABELS_PER_PAGE')
    template_name = 'gcse/label_list.html'


class CSELabelList(LabelList):
    """
    Render all the Labels for a Custom Search Engine in alphabetical order in a paged manner.
    """
    template_name = 'gcse/cse_label_list.html'

    def get_queryset(self):
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        self.cse = cse
        return cse.labels_counts()

    def get_context_data(self, *args, **kwargs):
        context = super(CSELabelList, self).get_context_data(**kwargs)
        context['cse'] = self.cse
        context['count_facets'] = self.cse.facet_item_labels().count()
        context['count_labels'] = self.cse.all_labels().count() - context['count_facets']
        return context


class LabelDetail(ListView):
    """
    Show the Annotations for a Label across all CustomSearchEngines
    """
    context_object_name = 'annotation_list'
    model = Label
    paginate_by = settings.GCSE_CONFIG.get('NUM_ANNOTATIONS_PER_PAGE')
    slug_url_kwarg = 'id'
    slug_field = 'id'
    template_name = 'gcse/label_detail.html'

    def get_queryset(self):
        label = get_object_or_404(Label,
                                  pk=self.kwargs['id'])
        self.label = label
        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query) &
            Q(labels__in=[label])
            )
        return Annotation.objects.active().filter(qset).order_by('comment')#.prefetch_related()

    def get_context_data(self, *args, **kwargs):
        context = super(LabelDetail, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['label'] = self.label
        context['index'] = Annotation.alpha_list(selection=query, label_id=self.label.id)
        context['query'] = query
        context['total_count'] = Annotation.objects.active().filter(labels__in=(self.label,)).count()
        return context


class CSELabelDetail(LabelDetail):
    """
    Show the Annotations for a Label in a specific CustomSearchEngine.
    """
    template_name = 'gcse/cse_label_detail.html'

    def get_queryset(self):
        label = get_object_or_404(Label,
                                  pk=self.kwargs['id'])
        self.label = label

        query = self.request.GET.get('q', 'A')
        qset = (
            Q(comment__istartswith=query) &
            Q(labels__in=[label])
            )
        cse = get_object_or_404(CustomSearchEngine,
                                gid=self.kwargs['gid'])
        self.cse = cse
        return cse.annotations().filter(qset).order_by('comment').prefetch_related('labels')

    def get_context_data(self, *args, **kwargs):
        context = super(CSELabelDetail, self).get_context_data(**kwargs)
        query = self.request.GET.get('q', 'A')
        context['label'] = self.label
        context['index'] = Annotation.alpha_list(selection=query, label_id=self.label.id) # also filter by CSE
        context['query'] = query
        context['total_count'] = self.cse.annotation_count(label_id=self.label.id)
        context['cse'] = self.cse
        return context


def _all_labels_to_bitmasks(all_labels):
    """Given a list of Labels return a dict mapping the label names to a bitmask"""
    l_dict = {}
    for i, label in enumerate(all_labels):
        l_dict[label.name] = 1<<i
    return l_dict
