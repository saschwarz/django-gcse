from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from feeds import RssLatestFeed, AtomLatestFeed


feeds = {
    'rss': RssLatestFeed,
    'atom' : AtomLatestFeed,
}

urlpatterns = patterns('',
                       (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed',
                        {'feed_dict': feeds}),
                       )
urlpatterns += patterns('cse.views',
                        url(r'^$', 'index', name='cse_home'),
                        # urls for Google search related resources
                        url(r'^cse.xml$', direct_to_template, {'template': 'cse/cse.xml' }, name='cse'),
                        url(r'^googility_annotations.xml$', 'indexXML', name='cse_annotations'),
                        url(r'^results.html$', direct_to_template, {'template': 'cse/results.html' }, name='cse_results'),
                        # urls for browsing, searching, viewing, editing local site
                        url(r'^map/$', 'map', name='cse_map'),
                        url(r'^site/$', 'browse', name='cse_browse'), # browse by site name
                        url(r'^site/search/$', 'search', name='cse_search'),
                        url(r'^site/edit/(?P<id>\d+)/$', 'edit', name='cse_edit'),
                        url(r'^site/view/(?P<id>\d+)/$', 'view', name='cse_view'),

                        url(r'^site/label/$', 'browse_by_label_tabbed', name='cse_browse_by_label'), # browse by site labels
                        # internal label requests made by browse_by_label
                        # label.html loads a grid (which could be converted to happen in the tab select JS)
                        # label.json loads the data that populates the grid
                        url(r'^site/label/(?P<label>\w+).html$', 'browse_by_label_grid', name='cse_browse_by_label_grid'),
                        url(r'^site/label/(?P<label>\w+).json$', 'ajax_annotation', name='cse_ajax_annotation'),

                        url(r'^site/directions/(?P<id>\d+)/$', 'directions', name="cse_directions"),
                        url(r'^site/add/$', 'edit', {'add': True}, name='cse_add'),
                        url(r'^site/add/thanks/$', direct_to_template, {'template': 'cse/thanks.html'}, name='cse_thanks'),

                        # No longer used
                        url(r'^site/created/$', 'created', name='cse_created'),
                        url(r'^site/modified/$', 'modified', name='cse_modified'),
                        url(r'^todo/$', 'todo', name='cse_todo'),
                        url(r'^random/(?P<type>\w+)/$', 'random', name='cse_random'),
                        url(r'^submitted/$', 'submitted', name='cse_submitted'),
                        url(r'^site/images/$', 'images', name='cse_images'),
                        )
