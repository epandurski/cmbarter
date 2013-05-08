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
## This file contains django forms related to making deposits and
## withdrawal.
##
import re
from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

PROMISE_ID_VALUE = re.compile('^\d{1,9}$')


class FindCustomerForm(forms.Form):
    id = forms.RegexField(
        widget=forms.TextInput(attrs={'size' : '9'}),
        regex=r"^\d{9}$",
        max_length=9,
        label=_('Trader ID'),
        error_messages={'max_length': _('Enter a valid value.')})

    def clean_id(self):
        return int(self.cleaned_data['id'])


class MakeDepositForm(forms.Form):
    promise_id = forms.CharField(
        label=_('Product'),
        widget=widgets.Select(attrs={'class' : 'removethisprefixto_sort-onload'}))
    
    amount = forms.FloatField(
        label=_('Amount to deposit'),
        error_messages={'invalid':_('Enter a valid amount.')})

    subtract = forms.BooleanField(
        label=_('Withdraw the same amount from "My items for sale"'),
        required=False)
    
    reason = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}),
        label=_('Comment'),
        required=False,
        help_text=_("optional"))
    
    def clean_promise_id(self):
        piv = PROMISE_ID_VALUE.match(self.cleaned_data['promise_id'])
        return int(piv.group()) if piv else 0

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not (0.0 < amount < 1e16):
            raise forms.ValidationError(
                _('Enter a valid amount.'))
        else:
            return amount


class MakeWithdrawalForm(forms.Form):
    amount = forms.FloatField(
        label=_('Amount to withdraw'),
        error_messages={'invalid':_('Enter a valid amount.')},)

    reason = forms.CharField(
        max_length=300,        
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}),
        label=_('Comment'),        
        required=False,
        help_text=_("optional"))

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if not (0.0 < amount < 1e16):
            raise forms.ValidationError(
                _('Enter a valid amount.'))
        else:
            return amount
