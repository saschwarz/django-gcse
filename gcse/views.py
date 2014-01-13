from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.decorators.cache import never_cache
from django.core.mail import mail_managers
from django.core import urlresolvers
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from gcse.models import Annotation, Label
from gcse.forms import PlaceForm
from model_fields import get_labels_for
#from recaptcha.client import captcha

try:
    from django.utils import simplejson as json
except ImportError:
    import json


def indexXML(request, template='gcse/annotation.xml'):
    """
    Render all the active Annotations that have Google regular expressions.
    """
    return render_to_response(
        template,
        {'annotations': Annotation.active.exclude(about=''),
         }
        )


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
    admin_url = urlresolvers.reverse('admin:cse_annotation_change',
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
                return HttpResponseRedirect(reverse('cse_thanks'))
        else:  # new entry
            form = PlaceForm(request.POST)
            if captcha_error is '' and form.is_valid():
                instance = form.save(commit=False)
                instance.status = 'S'
                instance.save()
                form.save_m2m()
                edit_update_email(instance)
                return HttpResponseRedirect(reverse('cse_thanks'))
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

def browse_by_label_tabbed(request, template='gcse/browse_by_label_tabbed.html'):
    labels = [
        ('club', 'clubs'),
        ('equipment', 'equipment'),
        ('blog', 'blogs'),
        ('facility', 'facilities'),
        ('forum', 'forums'),
        ('general', 'general'),
        ('organization', 'orgs'),
        ('rental', 'rentals'),
        ('service', 'services'),
        ('store', 'stores'),
        ('training', 'training'),
        ('video', 'videos'),
        ]
    tab_index = 0
    tab = request.GET.get('label', None)
    if tab:
        for index, (singular, plural) in enumerate(labels):
            if (tab == singular):
                tab_index = index
                break;
    return render_to_response(template,
                              {"labels":labels,
                               "label":tab_index},
                              context_instance=RequestContext(request))

def browse_by_label_grid(request, label, template='gcse/browse_by_label_grid.html'):
    return render_to_response(template,
                              {'label': label},
                              context_instance=RequestContext(request))

# How to use jqGrid. First version
# ---------------------------------

def jqfilter(op,field):
    """We need to make the conversion from the search parameters that
    jqgrid sends and the sql ones.
    I you send a non existing condition it would apply the equal one"""

    jqgrid = {'bw': ("%s like %%s", "%s%%"  ),
              'eq': ("%s = %%s",    "%s"    ),
              'gt': ("%s > %%s",    "%s"    ),
              'ge': ("%s >= %%s",   "%s"    ),
              'ne': ("%s <> %%s",   "%s"    ),
              'lt': ("%s < %%s",    "%s"    ),
              'le': ("%s <= %%s",   "%s"    ),
              'ew': ("%s like %%s", "%%%s"  ),
              'cn': ("%s like %%s", "%%%s%%")
              }
    try:
        condition, template = jqgrid[op]
    except:
        condition, template = jqgrid['eq']
    return condition % field, template

class AjaxViewAnnotation:
    def __init__(self, annotation):
        self.state = annotation.state
        self.city = annotation.city
        self.comment = '<a href="%s">%s</a>' % (reverse('cse_view', kwargs={'id':annotation.id}), annotation.comment)
        self.labels = " ".join([l.name for l in annotation.labels.all()])

    @classmethod
    def json_encoder(cls, inst):
        return {'fields':{'comment':inst.comment, 'labels':inst.labels, 'city':inst.city, 'state':inst.state}}


def ajax_annotation(request, label):
    """Ajax needed by  jqgrid. This is not generic nor the best code you can have
    but for teaching purposes I prefer to sacrifice style.

    This code takes a python object, Person in our case and deals with pagination,
    and filters as is sent by jqGrid.
    """
    try:
        order = "id" if (request.GET.get('sidx')=="" or None) else request.GET.get('sidx')
        sort_order = "" if request.GET.get('sord') == "asc" else "-"
        order = sort_order+order
        page = int(request.GET.get('page'))
        rows = int(request.GET.get('rows'))
    except Exception:
        raise Http404
    # Here goes the model.
    query = Annotation.active.filter(Q(labels__name__exact=label))

    # We compute what we are going to present in the grid
    if request.GET.get('_search')=='true':
        # We're on searching mode
        searchField = request.GET.get('searchField')
        searchOp = request.GET.get('searchOper')
        field, template = jqfilter(searchOp, searchField)
        fields = [ field ]
        values = [ template  % request.GET.get('searchString')]
        try:
            total = query.all().extra(where=fields, params = values).count()
            rta = query.all().extra(where=fields, params = values)
        except Exception, e:
            data = '{"total":%(pages)s, "page":%(page)s, "records":%(total)s, "rows":%(rta)s }'\
                % {'pages':0, 'page':0, 'total':0, 'rta':None}
            return HttpResponse(data, mimetype="application/json")
    else:
        # Normal mode, so no filters applied
        rta = query.all()
        total = query.all().count()

    # Page calculation
    remainder = 1 if total % rows >0 else 0
    pages = total / rows  + remainder
    if page > pages:
        page = 1

    # Get just the data we needo for our page
    rta = rta.order_by(order)[(page-1)*rows:page*rows]

    # We build the json that jqgrid likes best :)
    rows = json.dumps([AjaxViewAnnotation(a) for a in rta], default=AjaxViewAnnotation.json_encoder)
    query = '{"total":%(pages)s, "page":%(page)s, "records":%(total)s, "rows":%(rta)s }' % {'pages':pages, 'page':page, 'total':total, 'rta':rows}
    return HttpResponse(query, mimetype='application/json')

def browse_by_label(request, label, template='gcse/browse_by_label_div.html'):
    query_set = Annotation.active.filter(labels__name__exact=label).distinct().order_by('comment')
    paginator = Paginator(query_set, 20)

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        annotations = paginator.page(page)
    except (EmptyPage, InvalidPage):
        annotations = paginator.page(paginator.num_pages)
    return render_to_response(template,
                              {"annotations": annotations,
                               "label":label
                               },
                              context_instance=RequestContext(request))


def browse(request, q="A", num=20, template='gcse/browse.html'):
    """Render the Annotations in alphabetical order in a paged manner"""
    query = request.GET.get('q', q)
    if query:
        qset = (
            Q(comment__istartswith=query)
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
        annotations = paginator.page(page)
    except (EmptyPage, InvalidPage):
        annotations = paginator.page(paginator.num_pages)
    index = Annotation.alpha_list(query)
    return render_to_response(template,
                              {'annotations': annotations,
                               'index': index,
                               'query': query},
                              context_instance=RequestContext(request))
