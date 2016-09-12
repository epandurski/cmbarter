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
## This file contains django forms related to user's profiles and for
## managing trading partners.
##
from cStringIO import StringIO  # PYTHON3: from io import BytesIO
from django import forms
from django.forms import widgets
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils.functional import keep_lazy
    allow_lazy = lambda func, *resultclasses: keep_lazy(*resultclasses)(func)
except:
    from django.utils.functional import allow_lazy
from django.core.files.uploadhandler import FileUploadHandler
from django.core.files.uploadedfile import UploadedFile

format_lazy = allow_lazy(lambda x, y: x%y, unicode)


class PhotographUploadHandler(FileUploadHandler):
    """
    File upload handler to stream photograph uploads into memory.
    """

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        # Check the content-length header to see if we should keep the data.
        if content_length > settings.CMBARTER_MAX_IMAGE_SIZE + 10000:
            self.__keep = False
        else:
            self.__keep = True

    def new_file(self, field_name, file_name, content_type, *args, **kwargs):
        self.__file_name = file_name
        self.__content_type = content_type
        self.__file = StringIO()  # PYTHON3: self.__file = BytesIO()

    def receive_data_chunk(self, raw_data, start):
        if self.__keep:
            self.__file.write(raw_data)

    def file_complete(self, file_size):
        self.__file.seek(0)
        return UploadedFile(
            file = self.__file,
            name = self.__file_name,
            content_type = self.__content_type,
            size = file_size if self.__keep else 0,
            charset = None
            )


class FindTraderForm(forms.Form):
    id = forms.RegexField(
        widget=forms.TextInput(attrs={'size' : '9'}),
        regex=r"^[0-9]{9}$",
        max_length=9,
        label=_('Trader ID'),
        error_messages={'max_length': _('Enter a valid value.')})

    def clean_id(self):
        return int(self.cleaned_data['id'])


class EditProfileForm(forms.Form):
    full_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'size' : '30'}),
        label=_('Full name'))
    summary = forms.CharField(
        label=_('A short summary about you or your business'),
        max_length=300,
        widget=forms.Textarea(attrs={'class' : 'short_textarea'}))
    email = forms.EmailField(
        label=_('Email'),        
        max_length=100,
        widget=forms.TextInput(attrs={'size' : '30'}))
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
        max_length=25,
        widget=forms.TextInput(attrs={'size' : '15'}))
    country = forms.CharField(
        required=False,
        label=_('Country'),        
        max_length=50,
        widget=forms.TextInput(attrs={'size' : '30'}))
    advertise_trusted_partners = forms.BooleanField(
        required=False,
        label=_('Allow other traders to see your partners list'))
    time_zone = forms.CharField(
        label=_('Time zone'),        
        max_length=300,
        widget=widgets.Select)
    
    def clean_summary(self):
        summary = self.cleaned_data['summary'].strip()
        if summary:
            return summary
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name'].strip()
        if full_name:
            return full_name
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
        


class UploadPhotographForm(forms.Form):    
    photo = forms.ImageField(
        widget=forms.FileInput(attrs={'size': '30', 'accept': 'image/*'}),
        error_messages={
            'empty': format_lazy(
                _('ERROR: The file should not be empty or bigger than %(max_size)sKB.'),
                {'max_size': str(settings.CMBARTER_MAX_IMAGE_SIZE // 1024)} )},
        label=_('Image file'))


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput(),
        error_messages={'max_length': _('Ensure this value has at most 64 characters.') },
        label=_('Enter your old password'))

    password = forms.CharField(
        min_length=settings.CMBARTER_MIN_PASSWORD_LENGTH,
        max_length=64,
        widget=forms.PasswordInput(),
        label=_('Choose a new password'),
        error_messages={
            'min_length': format_lazy(
                _('Ensure this value has at least %(min_length)s characters.'),
                {'min_length': str(settings.CMBARTER_MIN_PASSWORD_LENGTH)}),
            'max_length': _('Ensure this value has at most 64 characters.') },
        help_text=format_lazy( _('at least %(min_length)s characters'),
                               {'min_length': str(settings.CMBARTER_MIN_PASSWORD_LENGTH)} ))
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(),
        label=_('Re-enter the new password'))

    def clean(self):
        if ('password' in self.cleaned_data and
            'password2' in self.cleaned_data and
            self.cleaned_data['password2'] != self.cleaned_data['password']):
            raise forms.ValidationError(
                _('ERROR: New passwords do not match.'))
        return self.cleaned_data          


class ChangeUsernameForm(forms.Form):
    username = forms.CharField(
        max_length=32,
        label=_('Choose a new username'))
    
    password = forms.CharField(
        max_length=64,
        widget=forms.PasswordInput(),
        error_messages={'max_length': _('Ensure this value has at most 64 characters.') },
        label=_('Enter your password'))

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if username:
            return username
        else:
            raise forms.ValidationError(_('This field is required.'))


class AddPartnerForm(forms.Form):
    name = forms.CharField(
        max_length=50,        
        label=_('Name'))

    comment = forms.CharField(
        required=False,
        max_length=600,
        widget=forms.Textarea(attrs={'class' : 'medium_textarea'}),
        label=_('Summary'),
        help_text=_('optional'))

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if name:
            return name
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_comment(self):
        return self.cleaned_data['comment'].strip()


class RemovePartnerForm(forms.Form):
    agreed = forms.BooleanField(
        label=_('I confirm'),
        error_messages= \
        {'required': _('You must confirm your wish before submitting.')})


class EmailCustomersForm(forms.Form):
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'size' : '50'}),
        label=_('Subject'))

    content = forms.CharField(
        max_length=5000,        
        widget=forms.Textarea(attrs={'rows' : '11', 'cols' : '65'}),
        label=_('Write your message here'))

    def clean_subject(self):
        subject = self.cleaned_data['subject'].strip()
        if subject:
            return subject
        else:
            raise forms.ValidationError(_('This field is required.'))

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if content:
            return content
        else:
            raise forms.ValidationError(_('This field is required.'))
