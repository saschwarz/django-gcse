from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template


urlpatterns = patterns('cse.views',
                       url(r'^$', 'index', name='cse_home'),
                       # urls for Google search related resources
                       url(r'^annotations.xml$', 'indexXML', name='cse_annotations'),
                       url(r'^results.html$', direct_to_template, {'template': 'cse/results.html' }, name='cse_results'),
                       url(r'^cse.xml$', direct_to_template, {'template': 'cse/cse.xml' }, name='cse'),

                       url(r'^map/$', 'map', name='cse_map'),
                       url(r'^site/$', 'browse', name='cse_site_browse'),
                       url(r'^site/search/$', 'search', name='cse_search'),
                       url(r'^site/edit/(?P<id>\d+)/$', 'edit', name='cse_edit'),
                       url(r'^site/view/(?P<id>\d+)/$', 'view', name='cse_annotation_detail'),
                       url(r'^site/label/$', 'browse_by_label_tabbed', name='cse_browse_by_label'),

                       # internal requests
                       url(r'^site/label/(?P<label>\w+).html$', 'browse_by_label_grid', name='cse_browse_sites_by_label'),
                       url(r'^site/label/(?P<label>\w+).json$', 'ajax_annotation'),

                       (r'^site/edit/$', 'edit'),
                       url(r'^site/directions/(?P<id>\d+)/$', 'directions', name="cse_directions"),
                       url(r'^site/add/$', 'edit', {'add': True}, name='cse_add_site'),
                       url(r'^site/add/thanks/$', direct_to_template, {'template': 'cse/thanks.html'}, name='cse_thanks'),
                       (r'^todo/$', 'todo'),
                       (r'^site/images/$', 'images'),

                       # Still needed?
                       (r'^random/(?P<type>\w+)/$', 'random'),
                       (r'^created/$', 'created'),
                       (r'^modified/$', 'modified'),
                       (r'^submitted/$', 'submitted'),
                       # needed for index template
                       url(r'^pretend_search/$', 'images', name='haystack_search'),
                       url(r'^help/$', 'images', name='help'),
                       url(r'^about/$', 'images', name='about'),
                       url(r'^advertising/$', 'images', name='advertising'),
                       url(r'^faq/$', 'images', name='faq'),
                       url(r'^contact/$', 'images', name='contact_form'),
                       url(r'^periodicals/$', 'images', name='periodicals_list'),
                       )
