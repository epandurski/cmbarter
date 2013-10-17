## The author disclaims copyright to this source code.  In place of
## a legal notice, here is a poem:
##
##   "Metaphysics"
##   
##   Matter: is the music 
##   of the space.
##   Music: is the matter
##   of the soul.
##   
##   Soul: is the space
##   of God.
##   Space: is the soul
##   of logic.
##   
##   Logic: is the god
##   of the mind.
##   God: is the logic
##   of bliss.
##   
##   Bliss: is a mind
##   of music.
##   Mind: is the bliss
##   of the matter.
##   
######################################################################
## This file contains django forms related to user's pricelist and
## user's shopping list.
##
import re
from django import forms
from django.utils.translation import ugettext_lazy as _


class CreateProductForm(forms.Form):
    _SBU = re.compile(r'^\s*\[(.*)\]\s*$')
    
    title = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'size' : '30'}),
        label=_('Title'),
        help_text=_('preferably in plural form, e.g. "Music lessons" or "Cars"'))

    unit = forms.CharField(
        max_length=50,        
        label=_('Unit of measurement'),
        help_text=_('preferably in singular form, e.g. "hour" or "one"'))

    summary = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={'class' : 'medium_textarea'}),
        label=_('Short summary'))

    epsilon = forms.FloatField(
        widget=forms.TextInput(attrs={'size' : '10'}),
        label=_("Roundoff amount"),
        help_text=_("""
          An amount in units of this product that's small enough that
          it can be neglected, e.g. "0.001". This is used when rounding off numbers
          for display.
        """))

    description = forms.CharField(
        required=False,
        max_length=5000,        
        widget=forms.Textarea(attrs={'class' : 'large_textarea'}),
        label=_('A more detailed description'),
        help_text=_("optional"))

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if title:
            return title
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_unit(self):
        sbu = CreateProductForm._SBU.match(self.cleaned_data['unit'])
        unit = (sbu.group(1).strip() if sbu else self.cleaned_data['unit']).strip()
        if unit:
            return unit
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_summary(self):
        summary = self.cleaned_data['summary'].strip()
        if summary:
            return summary
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_epsilon(self):
        epsilon = self.cleaned_data['epsilon']
        if epsilon < 1e-16 or epsilon != epsilon:
            raise forms.ValidationError(
                _('Ensure this value is greater than zero.'))
        else:
            return min(epsilon, 1e+16)

    def clean_description(self):
        return self.cleaned_data['description'].strip()


class AddItemForm(forms.Form):
    add = forms.BooleanField(
        required=False,        
        label=_('Add this product to my shopping list'))


class RemoveProductForm(forms.Form):
    remove = forms.BooleanField(
        required=False,        
        label=_('Remove this product from my pricelist'))
