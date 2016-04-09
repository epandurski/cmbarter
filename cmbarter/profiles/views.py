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
## This file contains django view-functions implementing functionality
## related to user's profiles and managing trading partners.
##
import threading
from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
try:
    from django.template.context_processors import csrf
except:
    from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.translation import ugettext_lazy as _
from cStringIO import StringIO  # PYTHON3: from io import BytesIO
from cmbarter.users.decorators import has_profile, logged_in, CmbAppError
from cmbarter.profiles import forms
from cmbarter.modules import curiousorm, utils
from pytz import common_timezones

# Try to import PIL in either of the two ways it can end up installed.
try:
    from PIL import Image
except ImportError:
    import Image

image_processing_lock = threading.Lock()


db = curiousorm.Database(settings.CMBARTER_DSN, dictrows=True)


@has_profile(db)
def show_image(request, user, trader_id_str, photograph_id_str):

    # Get the image.
    request._cmbarter_trx_cost += 1.0
    img = db.get_image(int(trader_id_str), int(photograph_id_str))
    
    if img:
        # Render the image with the right MIME-type.
        img_buffer = img['raw_content']
        response = HttpResponse(img_buffer, content_type='image/jpeg')
        response['Content-Encoding'] = 'identity'
        response['Content-Length'] = len(img_buffer)
        response['Cache-Control'] = "max-age=12096000, public"
        return response

    return HttpResponseRedirect(reverse('profiles-no-image'))


@has_profile(db)
def find_trader(request, user, tmpl='find_trader.html'):
    if request.method == 'POST':
        form = forms.FindTraderForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 1.0
            if db.get_profile(form.cleaned_data['id']):
                
                return HttpResponseRedirect(reverse(
                    show_profile,
                    args=[user['trader_id'], form.cleaned_data['id']]))
            else:
                form.wrong_trader_id = True
    else:
        form = forms.FindTraderForm()

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user': user, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
@curiousorm.retry_on_deadlock
def check_email_verification(request, user, tmpl='email_not_verified.html'):

    # Profile-emails that have not been verified for more than 1 month
    # are set to ''.  If so, the user sees a notification page.  We do
    # not insist on emails being verified in case our server happens
    # to be blacklisted.
    if not settings.CMBARTER_HOST_IS_SPAM_LISTED:
        wrong_email = db.find_failed_email_verification(user['trader_id'])

        if wrong_email:
            # Render the notification page with CSRF protection.
            c = {'settings': settings, 'user': user, 'wrong_email': wrong_email }
            c.update(csrf(request))
            return render_to_response(tmpl, c)

    return HttpResponseRedirect(reverse(
        'products-shopping-list', args=[user['trader_id']]))


@has_profile(db)
def show_profile(request, user, trader_id_str, tmpl='contact_information.html'):

    # Get trader's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(int(trader_id_str))

    # Get trader's pending email verification if there is one.
    email_verification = db.get_email_verification(int(trader_id_str))
    
    if trader:
        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user': user, 'trader': trader, 
             'email_verification': email_verification or {} }
        c.update(csrf(request))
        return render_to_response(tmpl, c)
    
    return HttpResponseRedirect(reverse(
        find_trader,
        args=[user['trader_id']]))


@has_profile(db)
@curiousorm.retry_on_deadlock
def edit_profile(request, user, tmpl='edit_contact_information.html'):
    if request.method == 'POST':
        form = forms.EditProfileForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 5.0
            db.update_profile(user['trader_id'],
                form.cleaned_data['full_name'],
                form.cleaned_data['summary'],
                form.cleaned_data['country'],
                form.cleaned_data['postal_code'],
                form.cleaned_data['address'],
                form.cleaned_data['email'],
                form.cleaned_data['phone'],
                form.cleaned_data['fax'],
                form.cleaned_data['www'],
                form.cleaned_data['time_zone'],
                form.cleaned_data['advertise_trusted_partners'])
            
            return HttpResponseRedirect(reverse(
                show_profile,
                args=[user['trader_id'], user['trader_id']]))
    else:
        form = forms.EditProfileForm(
            initial=db.get_profile(user['trader_id']))

    # Fetches all known time zones in the form's time-zone-select-box.
    form.fields['time_zone'].widget.choices = [
        ('', _('Select your time zone'))] + [
        (tz, tz) for tz in common_timezones]

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def upload_photograph(request, user, tmpl='upload_photograph.html'):
    if request.method == 'POST':
        request._cmbarter_trx_cost += 2.0
        photograph_id = db.generate_photograph_id(user['trader_id'])
        if not photograph_id:
            return HttpResponseRedirect(reverse(
                show_profile,
                args=[user['trader_id'], user['trader_id']]))
        
        form = forms.UploadPhotographForm(request.POST, request.FILES)
        if form.is_valid():
            form.file_too_big = True  # This will be the message shown if something goes wrong.
            uploaded_file = request.FILES['photo']
            if uploaded_file.size <= settings.CMBARTER_MAX_IMAGE_SIZE:
                img = Image.open(uploaded_file)
                width, height = img.size
                pixels = max(width, 32) * max(height, 32)
                if pixels <= settings.CMBARTER_MAX_IMAGE_PIXELS:
                    request._cmbarter_trx_cost += (pixels / 1e4)

                    # The image processing may consume a lot of
                    # memory, which is a potential DoS-attack
                    # vector. Therefore we acquire a threading lock so
                    # as to make sure one process does at most one big
                    # memory allocation at a time.
                    image_processing_lock.acquire()
                    try:
                        # Crop the image if the height is too big.
                        max_height = width * 3 // 2
                        if height > max_height:
                            height = max_height
                            img = img.crop((0, 0, width, height))

                        # Resize the image to 220px width, and convert it to proper color-mode.
                        img = img.resize((220, 220 * height // width), Image.ANTIALIAS)
                        img = img.convert()

                        # Serialize the image as JPEG.
                        s = StringIO()  # PYTHON3: s = BytesIO()
                        img.save(s, 'JPEG')

                    except:
                        raise CmbAppError

                    finally:
                        img = None
                        image_processing_lock.release()

                    # Store the resized image to the DB.
                    request._cmbarter_trx_cost += 8.0
                    jpeg_bytea = curiousorm.Binary(s.getvalue())
                    db.replace_profile_photograph(user['trader_id'], photograph_id, jpeg_bytea)

                    return HttpResponseRedirect(reverse(
                        show_profile,
                        args=[user['trader_id'], user['trader_id']]))

    else:
        form = forms.UploadPhotographForm()

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user' : user, 'form': form }
    c.update(csrf(request))    
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def change_password(request, user, tmpl='change_password.html'):
    if request.method == 'POST':
        form = forms.ChangePasswordForm(request.POST)
        if form.is_valid():
            password_salt = db.get_password_salt(user['username'])
            request._cmbarter_trx_cost += 2.0
            if db.update_password(
                  user['trader_id'],
                  utils.calc_crypt_hash(password_salt + form.cleaned_data['old_password']),
                  utils.calc_crypt_hash(password_salt + form.cleaned_data['password'])):

                return HttpResponseRedirect(reverse(
                    report_change_password_success,
                    args=[user['trader_id']]))
            else:
                form.wrong_password = True
    else:
        form = forms.ChangePasswordForm()

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user' : user, 'form': form }
    c.update(csrf(request))    
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def change_username(request, user, tmpl='change_username.html'):
    if request.method == 'POST':
        form = forms.ChangeUsernameForm(request.POST)
        if form.is_valid():
            password_salt = db.get_password_salt(user['username'])
            request._cmbarter_trx_cost += 4.0
            error = db.update_username(
                  user['trader_id'],
                  utils.calc_crypt_hash(password_salt + form.cleaned_data['password']),
                  form.cleaned_data['username'])

            if 2==error:
                form.wrong_password = True

            elif 1==error:
                form.username_taken = True
                
            else:    
                return HttpResponseRedirect(reverse(
                    report_change_username_success,
                    args=[user['trader_id']]))
    else:
        form = forms.ChangeUsernameForm()

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user' : user, 'form': form }
    c.update(csrf(request))    
    return render_to_response(tmpl, c)


@has_profile(db)
def report_change_password_success(request, user, tmpl='change_password_success.html'):
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user' : user }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def report_change_username_success(request, user, tmpl='change_username_success.html'):
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user' : user }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_partners(request, user, tmpl='partners.html'):

    # Get user's list of partners.
    partners = db.get_trust_list(user['trader_id'])

    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user': user, 'partners' : partners }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def add_partner(request, user, partner_id_str, tmpl='add_partner.html'):
    partner_id = int(partner_id_str)

    if request.method == 'POST':
        # Initialize the form
        form = forms.AddPartnerForm(request.POST)

        # Try to add the partner and skip the rest if everything is OK.
        if form.is_valid():
            request._cmbarter_trx_cost += 4.0
            if db.replace_trust(
                user['trader_id'],
                partner_id,
                form.cleaned_data['name'],
                form.cleaned_data['comment']):

                return HttpResponseRedirect(reverse(
                    'products-partner-pricelist',
                    args=[user['trader_id'], partner_id]))
            else:
                form.name_collision = True

        # Get partner's profile.
        request._cmbarter_trx_cost += 1.0                
        trader = db.get_profile(partner_id)
        if not trader:
            raise Http404
        
    else:
        # Get partner's profile.
        request._cmbarter_trx_cost += 1.0
        trader = db.get_profile(partner_id)
        if not trader:
            raise Http404

        # Initialize the form        
        form = forms.AddPartnerForm(initial=(
            db.get_trust(user['trader_id'], partner_id)
            or
            {'name': trader['full_name'], 'comment': trader['summary']}))

    # Render everything adding CSRF protection.        
    c =  {'settings': settings, 'user' : user, 'trader': trader, 'form' : form }
    c.update(csrf(request))    
    return render_to_response(tmpl, c)
    

@has_profile(db)
@curiousorm.retry_on_deadlock
def remove_partner(request, user, partner_id_str, tmpl='remove_partner.html'):
    partner_id = int(partner_id_str)

    if request.method == 'POST':
        form = forms.RemovePartnerForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 4.0
            db.delete_trust(user['trader_id'], partner_id)
            
            return HttpResponseRedirect(reverse(
                show_partners,
                args=[user['trader_id']]))
    else:
        form = forms.RemovePartnerForm()

    # Get partner's profile.
    trust = db.get_trust(user['trader_id'], partner_id)
    
    if trust:
        # Render everything adding CSRF protection.        
        c =  {'settings': settings, 'user' : user, 'trust': trust, 'form' : form }
        c.update(csrf(request))    
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
def show_suggested_partners(request, user, partner_id_str, tmpl='suggested_partners.html'):
    partner_id = int(partner_id_str)

    # Get partner's profile.
    trust = db.get_trust(user['trader_id'], partner_id)
    
    if trust:
        request._cmbarter_trx_cost += 1.0
        if db.get_profile(partner_id)['advertise_trusted_partners']==False:
            # We are NOT ALLOWED to show this info -- return empty result set.
            query = ''
            current_page = 1
            number_of_items, number_of_pages, number_of_items_per_page = 0, 0, 1
            visible_items = []
        else:
            # We are ALLOWED to show this info -- Parse GET-ed parameters and query the database.
            query = request.GET.get('q', u'')[:70]
            try:
                current_page = max(int(request.GET.get('page', u'')[:3]), 1)
            except ValueError:
                current_page = 1
            number_of_items, number_of_pages, number_of_items_per_page = db.get_trust_match_count(
                partner_id, query)
            visible_items = db.get_trust_match_list(partner_id, query, current_page - 1)

        # Render everything adding CSRF protection.
        a = (current_page - 1) * number_of_items_per_page + 1
        b = 5
        c =  {'settings': settings, 'user' : user, 'trust': trust,
              'query': query, 'current_page': current_page,
              'number_of_items': number_of_items,
              'number_of_pages': number_of_pages,
              'number_of_items_per_page': number_of_items_per_page,
              'visible_items': visible_items,
              'first_visible_item_seqnum': a,
              'last_visible_item_seqnum': a - 1 + (
                len(visible_items) if len(visible_items) > 0 else number_of_items_per_page),
              'visible_pages': range(
                max(1, current_page - b + 1), 
                1 + min(number_of_pages, current_page + b)) 
              }
        c.update(csrf(request))    
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
@curiousorm.retry_on_deadlock
def email_customers(request, user, tmpl='email_customers.html'):

    # We should check first if the user has successfully verified
    # his/her email address.
    verified_email = db.get_verified_email(user['trader_id'])

    if not verified_email:
        form = None
    
    elif request.method == 'POST':
        form = forms.EmailCustomersForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 3.0
            if db.insert_outgoing_customer_broadcast(
                user['trader_id'],
                verified_email['email'],
                form.cleaned_data['subject'],
                form.cleaned_data['content']):
            
                return HttpResponseRedirect(reverse(
                    report_email_customers_success,
                    args=[user['trader_id']]))
            else:
                form.email_quota_exceeded = True
                
    else:
        form = forms.EmailCustomersForm()

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_email_customers_success(request, user, tmpl='email_customers_success.html'):
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user' : user }
    c.update(csrf(request))
    return render_to_response(tmpl, c)

