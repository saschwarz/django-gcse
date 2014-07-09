from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from datetime import datetime

from .models import Annotation


class RssLatestFeed(Feed):
    author_name = "Steve Schwarz"
    author_link = "http://agilitynerd.com/static/about.html"
    author_email = "steve@agilitynerd.com"
    title = "Googility Additions/Changes"
    description = "Additions and changes to sites listed on Googility.com"
    link = "/feeds/rss/"

    def copyright(self):
        return "Copyright (c) %s, Steve Schwarz" % (datetime.now().year)

    def items(self):
        return Annotation.objects.filter(status='A').order_by('-modified')[:10]


class AtomLatestFeed(RssLatestFeed):
    feed_type = Atom1Feed
    subtitle = RssLatestFeed.description
    link = "/feeds/atom/"

    def item_pubdate(self, item):
        return item.modified
