# From http://nathanostgard.com/archives/2007/7/25/field-labels-in-templates/
from string import capwords


def get_labels_for(model, cap=True, esc=True):
  from django.template.defaultfilters import capfirst
  from django.utils.html import escape
  labels = {}
  for field in model._meta.fields:
    label = field.verbose_name
    if cap is True:
      label = capfirst(label)
    elif cap == 'All':
      label = capwords(label)
    if esc:
      label = escape(label)
    labels[field.name] = label
  return labels

def with_labels(context, cap=True, esc=True):
  from django.db.models import Model
  result = context.copy()
  for k, v in context.iteritems():
    if isinstance(v, Model):
      result[k + '_labels'] = get_labels_for(v, cap, esc)
    elif hasattr(v, '__getitem__') and len(v) > 0:
      if isinstance(v[0], Model):
        result[k + '_labels'] = get_labels_for(v[0], cap, esc)
  return result
