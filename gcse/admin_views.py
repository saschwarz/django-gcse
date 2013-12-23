from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.db import transaction
from django.template import loader, Context
from django.core.mail import send_mail
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.sites.models import Site
from django.conf import settings
from gcse.models import AnnotationSAXHandler, Annotation
from gcse.forms import ImportForm


@staff_member_required
@transaction.autocommit
def importAnnotations(request):
    """Import the content of an Annotations file"""
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            handler = AnnotationSAXHandler()
            if form.cleaned_data['url'] != '':
                handler.parse(str(form.cleaned_data['url']))
            else:
                handler.parseString(request.FILES['fileName'].read())
            # redirect to the annotation screen to see the results
            return HttpResponseRedirect('/admin/cse/annotation/')
    else:
        form = ImportForm()
    return render_to_response('admin/cse/import.html', {'form': form})


@staff_member_required
def send_submission_reply(request, id):
    site = get_object_or_404(Annotation, pk=id)
    c = Context({'site': site, })
    if site.submitter_email:
        t = loader.get_template('submission_reply.txt')
        send_mail('%s updated for %s' % (Site.objects.get_current().__getattribute__("name"), site.comment),
                  t.render(c), settings.EMAIL_HOST_USER, [site.submitter_email,], fail_silently=False)
        # remove the submitter's email address
        site.submitter_email = ''
        site.save()
    if site.email:
        t = loader.get_template('updated_email.txt')
        send_mail('%s updated for %s' % (Site.objects.get_current().__getattribute__("name"), site.comment),
                  t.render(c), settings.EMAIL_HOST_USER, [site.email,], fail_silently=False)

    return HttpResponseRedirect('/admin/cse/annotation/?status__exact=S')
