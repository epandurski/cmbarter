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
## This file contains django forms related to singing up, logging in,
## and completing users' profiles.
##
from django import forms
from django.forms import widgets
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import allow_lazy

format_lazy = allow_lazy(lambda x, y: x%y, unicode)


class SignupForm(forms.Form):
    username = forms.CharField(
        max_length=32,
        label=_('Choose a username'))

    password = forms.CharField(
        min_length=settings.CMBARTER_MIN_PASSWORD_LENGTH,
        max_length=64,
        widget=forms.PasswordInput(),
        label=_('Choose a password'),
        error_messages={
            'min_length': format_lazy(
                _('Ensure this value has at least %(min_length)s characters.'),
                {'min_length': str(settings.CMBARTER_MIN_PASSWORD_LENGTH)}),
            'max_length': _('Ensure this value has at most 64 characters.') },
        help_text=format_lazy( _('at least %(min_length)s characters'),
                               {'min_length': str(settings.CMBARTER_MIN_PASSWORD_LENGTH)} ))
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(),
        label=_('Re-enter the password'))

    registration_key = forms.CharField(
        required=settings.CMBARTER_REGISTRATION_KEY_IS_REQUIRED,
        max_length=32,
        label=_('Enter your registration key'))

    def clean(self):
        if ('password' in self.cleaned_data and
            'password2' in self.cleaned_data and
            self.cleaned_data['password2'] != self.cleaned_data['password']):
            raise forms.ValidationError(
                _('ERROR: Passwords do not match.'))
        return self.cleaned_data          

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username:
            return username
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_registration_key(self):
        return self.cleaned_data['registration_key'].replace(' ', '').replace('-', '')


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=32,
        label=_("Your username"))
    
    password = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput,
        error_messages={'max_length': _('Ensure this value has at most 64 characters.') },
        label=_("Your password"))

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username:
            return username
        else:
            raise forms.ValidationError(_('This field is required.'))



class CreateProfileForm(forms.Form):
    full_name = forms.CharField(
        label=_('Full name'),
        max_length=50,
        widget=forms.TextInput(attrs={'size' : '30'}),
        help_text='<span class="highlighted">*</span>')
    summary = forms.CharField(
        label=_('A short summary about you or your business'),
        max_length=300,
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}),
        help_text='<span class="highlighted">*</span>')
    email = forms.EmailField(
        label=_('Email'),
        max_length=100,                             
        widget=forms.TextInput(attrs={'size' : '30'}),
        help_text='<span class="highlighted">*</span>')
    www = forms.URLField(
        required=False,
        max_length=100,                                                    
        widget=forms.TextInput(attrs={'size' : '30'}),
        label=_('Home page'))
    phone = forms.RegexField(
        required=False,
        regex=r'^ *\+?[0-9.() -]*[0-9][0-9.() -]*$',        
        label=_('Phone'),
        max_length=50,                            
        widget=forms.TextInput(attrs={'size' : '15'}))
    fax = forms.CharField(
        required=False,
        label=_('Fax'),
        max_length=50,                          
        widget=forms.TextInput(attrs={'size' : '15'}))
    address = forms.CharField(
        required=False,
        label=_('Address'),        
        max_length=200,                              
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}))
    postal_code = forms.CharField(
        required=False,
        label=_('Postal code'),        
        max_length=50,                                  
        widget=forms.TextInput(attrs={'size' : '15'}))
    country = forms.CharField(
        required=False,
        label=_('Country'),
        max_length=50,                              
        widget=forms.TextInput(attrs={'size' : '30'}))
    time_zone = forms.CharField(
        label=_('Time zone'),
        max_length=300,
        widget=widgets.Select,
        help_text=('' if settings.CMBARTER_DEFAULT_USERS_TIME_ZONE 
                   else '<span class="highlighted">*</span>'))
    
    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if full_name:
            return full_name
        else:
            raise forms.ValidationError(_('This field is required.'))            

    def clean_summary(self):
        summary = self.cleaned_data['summary'].strip()
        if summary:
            return summary
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_www(self):
        return self.cleaned_data['www'].strip()
        
    def clean_phone(self):
        return self.cleaned_data['phone'].strip()
        
    def clean_fax(self):
        return self.cleaned_data['fax'].strip()
        
    def clean_address(self):
        return self.cleaned_data['address'].strip()
        
    def clean_postal_code(self):
        return self.cleaned_data['postal_code'].strip()
        
    def clean_country(self):
        return self.cleaned_data['country'].strip()



class CancelEmailForm(forms.Form):
    agreed = forms.BooleanField(
        label=format_lazy( _('I do not want to receive emails from %(host)s'),
                           {'host': settings.CMBARTER_HOST} ),
        error_messages= {'required': _('You must confirm your wish before submitting.')})


