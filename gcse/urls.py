from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from .feeds import RssLatestFeed, AtomLatestFeed
from .views import (AnnotationList, AnnotationDetail,
                    CSEAnnotations, CSEAnnotationList,
                    CustomSearchEngineList,
                    CustomSearchEngineDetail, CustomSearchEngineDetailXML,
                    CSELabelList, CSELabelDetail, LabelDetail, LabelList,
                    )


feeds = {
    'rss': RssLatestFeed,
    'atom': AtomLatestFeed,
}

urlpatterns = patterns('',
                       (r'^feeds/rss/$', RssLatestFeed()),
                       (r'^feeds/atom/$', AtomLatestFeed()),
                       )

urlpatterns += patterns('gcse.views',
                        url(r'^$', 'index', name="home"),
                        # urls for Google search related resources
                        url(r'^(?P<gid>[\w-]+).xml$',
                            CustomSearchEngineDetailXML.as_view(),
                            name='gcse_cse'),

                        url(r'^annotations/(?P<gid>[\w-]+).(?P<page>\w+).xml$',
                            CSEAnnotations.as_view(),
                            name='gcse_annotations'),

                        # display Google Search results
                        url(r'^results.html$',
                            TemplateView.as_view(template_name='gcse/results.html'),
                            name='gcse_results'),

                        # all CSEs
                        url(r'^cses/$',
                            CustomSearchEngineList.as_view(),
                            name='gcse_cse_list'),

                        # a single CSE
                        url(r'^cses/(?P<gid>[\w-]+)/$',
                            CustomSearchEngineDetail.as_view(),
                            name='gcse_cse_detail'),

                        # all Annotations
                        url(r'^annotations/$',
                            AnnotationList.as_view(),
                            name='gcse_annotation_list'),

                        # One Annotation
                        url(r'^annotations/(?P<id>.+)/$',
                            AnnotationDetail.as_view(),
                            name='gcse_annotation_detail'),

                        # Annotations for one CSE
                        url(r'^cses/(?P<gid>[\w-]+)/annotations/$',
                            CSEAnnotationList.as_view(),
                            name='gcse_cse_annotation_list'),

                        # all Labels
                        url(r'^labels/$',
                            LabelList.as_view(),
                            name="gcse_label_list"),

                        # One Label (all CSEs)
                        url(r'^cses/labels/(?P<id>.+)/$',
                            LabelDetail.as_view(),
                            name='gcse_label_detail'),

                        # Labels for one CSE
                        url(r'^cses/(?P<gid>[\w-]+)/labels/$',
                            CSELabelList.as_view(),
                            name='gcse_cse_label_list'),

                        # One CSE's Annotations for one Label
                        url(r'^cses/(?P<gid>.+)/labels/(?P<id>.+)/$',
                            CSELabelDetail.as_view(),
                            name='gcse_cse_label_detail'),

                        url(r'^site/search/$', 'search', name='gcse_search'),
                        # url(r'^site/edit/(?P<id>\d+)/$', 'edit', name='edit'),
                        # url(r'^site/view/(?P<id>\d+)/$', 'view', name='view'),
                        # url(r'^site/add/$', 'edit', {'add': True}, name='add'),
                        # url(r'^site/add/thanks/$', TemplateView.as_view(template_name='gcse/thanks.html'), name='thanks'),
                        )
