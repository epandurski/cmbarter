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
## This file contains django forms related to user's delivery orders.
##
from django import forms
from django.utils.translation import ugettext_lazy as _


class CreateOrderForm(forms.Form):
    amount = forms.FloatField(
        label=_('Amount of product'),
        error_messages={'invalid':_('Enter a valid amount.')})

    carrier = forms.CharField(
        max_length=50,
        label=_('Recipient'))

    instruction = forms.CharField(
        required=False,        
        max_length=300,
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}),
        label=_('Comment'),
        help_text=_("optional"))        

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not (0.0 < amount < 1e16):
            raise forms.ValidationError(
                _('Enter a valid amount.'))
        else:
            return amount

    def clean_carrier(self):
        carrier = self.cleaned_data['carrier'].strip()
        if carrier:
            return carrier
        else:
            raise forms.ValidationError(_('This field is required.'))


class RemoveOrderForm(forms.Form):
    remove = forms.BooleanField(
        required=False,
        label=_('Delete this payment order'))


class CompleteOrderForm(forms.Form):
    complete = forms.BooleanField(
        required=False,
        label=_('This payment order has been completed'))
