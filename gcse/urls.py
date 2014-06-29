from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from feeds import RssLatestFeed, AtomLatestFeed


feeds = {
    'rss': RssLatestFeed,
    'atom': AtomLatestFeed,
}

urlpatterns = patterns('',
                       (r'^feeds/rss/$', RssLatestFeed()),
                       (r'^feeds/atom/$', AtomLatestFeed()),
                       )

urlpatterns += patterns('gcse.views',
                        url(r'^$', 'index', name='cse_home'),
                        # urls for Google search related resources
                        url(r'^(?P<gid>[\w-]+).xml$', TemplateView.as_view(template_name='gcse/cse.xml'), name='cse'),
                        url(r'^annotations/(?P<gid>[\w-]+).(?P<index>[\d]+).xml$', 'indexXML', name='annotations'),

                        url(r'^results.html$', TemplateView.as_view(template_name='gcse/results.html'), name='cse_results'),
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
                        url(r'^site/add/thanks/$', TemplateView.as_view(template_name='gcse/thanks.html'), name='cse_thanks'),
                        )
