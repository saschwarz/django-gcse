from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from .feeds import RssLatestFeed, AtomLatestFeed
from .views import (CSEAnnotations, CustomSearchEngineDetail, AnnotationsList, browse_labels)


feeds = {
    'rss': RssLatestFeed,
    'atom': AtomLatestFeed,
}

urlpatterns = patterns('',
                       (r'^feeds/rss/$', RssLatestFeed()),
                       (r'^feeds/atom/$', AtomLatestFeed()),
                       )

urlpatterns += patterns('gcse.views',
                        url(r'^$', 'index', name='home'),
                        # urls for Google search related resources
                        url(r'^(?P<gid>[\w-]+).xml$', 
                            CustomSearchEngineDetail.as_view(),
                            name='cse'),
                        url(r'^annotations/(?P<gid>[\w-]+).(?P<page>\w+).xml$', 
                            CSEAnnotations.as_view(), 
                            name='cse_annotations'),

                        # display Google Search results
                        url(r'^results.html$', 
                            TemplateView.as_view(template_name='gcse/results.html'), 
                            name='cse_results'),

                        # urls for browsing, searching, viewing, editing local site
                        url(r'^site/$', 
                            AnnotationsList.as_view(),
                            name='cse_browse'), # browse by site name
                        url(r'^site/search/$', 'search', name='cse_search'),
                        url(r'^site/edit/(?P<id>\d+)/$', 'edit', name='edit'),
                        url(r'^site/view/(?P<id>\d+)/$', 'view', name='view'),
 
                        url(r'^site/label/$', 
                            'browse_labels', 
                            name='cse_browse_labels'), # browse all labels
                        url(r'^site/label/(?P<label>.+)$', 
                            'browse_label', 
                            name='browse_label'), # browse one label
                        url(r'^site/add/$', 'edit', {'add': True}, name='add'),
                        url(r'^site/add/thanks/$', TemplateView.as_view(template_name='gcse/thanks.html'), name='thanks'),
                        )
