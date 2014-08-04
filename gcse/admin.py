import re

from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib import admin
from django.forms import ModelForm, CharField, Textarea
from django.forms.models import ModelChoiceField, ModelMultipleChoiceField
from django.template.loader import render_to_string
from gcse.models import Label, Annotation, CustomSearchEngine, FacetItem
from ordered_model.admin import OrderedModelAdmin


class CustomSearchEngineForm(ModelForm):

    def clean_input_xml(self):
        # strip xml encoding so lxml is happy
        input_xml = self.cleaned_data["input_xml"]
        print(input_xml)
        if not input_xml:
            return ""
        result = re.sub(r'<\?xml.*\?>\r?\n?', '', input_xml)
        return result

    class Meta:
        model = CustomSearchEngine


class CustomSearchEngineAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'gid')
    save_on_top = True
    readonly_fields = ('output_xml',)
    form = CustomSearchEngineForm

admin.site.register(CustomSearchEngine, CustomSearchEngineAdmin)


class LabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'background', 'mode', 'weight', )
    list_filter = ('mode',)
    save_on_top = True

    class Meta:
        model = Label

admin.site.register(Label, LabelAdmin)


class AnnotationAdminForm(ModelForm):
    # Only allow non hidden fields to be selected as Labels
    labels = ModelMultipleChoiceField(Label.objects.filter(background=False))
    # Only allow hidden fields to be selected as Feed Labels
    feed_label = ModelChoiceField(Label.objects.filter(background=True), label='Feed Label')
    description = CharField(widget=Textarea(attrs={'rows':5, 'cols':60}), required=False)

    class Meta:
        model = Annotation


# class AnnotationModelAdmin(admin.ModelAdmin):
#     '''Provide a side by side editor for copying submitted Annotation fields to the active/parent Annotation.
#     Deletes delete the copy.'''
#     def change_view(self, request, object_id, extra_context=None):
#         updated = get_object_or_404(Annotation, pk=object_id)
#         active = updated.parent_version
#         if active:
#             # Edit the active Annotation and display the updated Annotation to copy from
#             object_id = str(active.id)
#             ModelForm = self.get_form(request, obj=updated)
#             if request.method == 'POST':
#                 # let the super class handle the save of the active annotation
#                 result = super(AnnotationModelAdmin, self).change_view(request, object_id, extra_context)
#                 if request.POST.has_key("_save_delete"):
#                     # active is saved. now delete the updated
#                     result = super(AnnotationModelAdmin, self).delete_view(request, str(updated.id), extra_context)
#                 # send the reply email to the submitter and owner using the object_id
#                 return HttpResponseRedirect(reverse('cse.admin_views.send_submission_reply', args=(object_id,)))
#             else: # GET of active with updated: add updated to context for rendering
#                 if not extra_context:
#                     extra_context = {}
#                 extra_context['sourceAnnotation'] = admin.helpers.AdminForm(ModelForm(instance=updated),
#                                                                             list(self.get_fieldsets(request)),
#                                                                             self.prepopulated_fields)
#         # change handling for non-updated annotations using GET and POST
#         return super(AnnotationModelAdmin, self).change_view(request, object_id, extra_context)


#class AnnotationAdmin(AnnotationModelAdmin):
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('comment', 'original_url', 'status', 'modified', 'created',)
    list_filter = ('status', 'labels', 'created', 'modified')
    search_fields = ['comment', 'about']
    save_on_top = True
#     form = AnnotationAdminForm


admin.site.register(Annotation, AnnotationAdmin)


class FacetItemAdmin(OrderedModelAdmin):
    list_display = ('title', 'move_up_down_links')

admin.site.register(FacetItem, FacetItemAdmin)
