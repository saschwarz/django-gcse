from django import template


from cse.models import Annotation

class AnnotationCountNode(template.Node):
    def __init__(self):
        pass

    def render(self, context):
        return str(Annotation.objects.filter(status='A').exclude(original_url='').count())


def do_annotation_count(parser, token):
    return AnnotationCountNode()

register = template.Library()
register.tag('annotation_count', do_annotation_count)
