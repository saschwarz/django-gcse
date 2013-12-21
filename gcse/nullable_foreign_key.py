from django.db import models, connection

class NullableForeignKey(models.ForeignKey):
    """
    Just like a ForeignKey, but when related objects are deleted this object is
    *not* deleted. As the name implies, this field is always NULLable.
    """

    def __init__(self, *args, **kwargs):
        kwargs['null'] = kwargs['blank'] = True
        super(NullableForeignKey, self).__init__(*args, **kwargs)

    # Monkey patches the related classes ``_collect_sub_objects`` method
    # to NULL out values in this field that point to the object that's about
    # to be deleted.
    # NOTE:  Override _collect_sub_objects rather than delete so a custom delete
    # method can still be used.
    def contribute_to_related_class(self, cls, related):
        super(NullableForeignKey, self).contribute_to_related_class(cls, related)

        # Alias so that the closure below has access to the outer "self"
        this_field = self

        # define a method name to map the original `_collect_sub_objects` method to
        _original_csb_attr_name = '_original_collect_sub_objects'

        def _new_collect_sub_objects(self, *args, **kwargs):
            # NULL out anything related to this object.
            qn = connection.ops.quote_name
            for related in self._meta.get_all_related_objects():
                if isinstance(related.field, this_field.__class__):
                    table = qn(related.model._meta.db_table)
                    column = qn(related.field.column)
                    sql = "UPDATE %s SET %s = NULL WHERE %s = %%s;" % (table, column, column)
                    connection.cursor().execute(sql, [self.pk])

            # Now proceed with collecting sub objects that are still tied via FK
            getattr(self, _original_csb_attr_name)(*args, **kwargs)

        # monkey patch the related classes _collect_sub_objects method.
        # store the original method in an attr named `_original_csb_attr_name`
        if not hasattr(cls, _original_csb_attr_name):
            setattr(cls, _original_csb_attr_name, cls._collect_sub_objects)
            setattr(cls, '_collect_sub_objects', _new_collect_sub_objects)
