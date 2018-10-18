from django.contrib.auth import login, logout
from django.shortcuts import render
from django.shortcuts import redirect
from django.views import View
from dropbox import dropbox
from dropbox import DropboxOAuth2Flow
from dropbox.oauth import BadRequestException, BadStateException, CsrfException, NotApprovedException, ProviderException
from django.http import HttpResponse

from demo import settings


class Api(View):

    def get(self, request):
        dropbox_auth_finish(request)
        if request.user.is_authenticated:
            dbx = dropbox.Dropbox(request.session['dropbox']['token'])
            return render(request, 'index.html', context={'files': dbx.files_list_folder('').entries})
        return render(request, 'login.html')


class Dropbox(View):

    def get(self, request):
        authorize_url = get_dropbox_auth_flow(request.session).start()
        return redirect(authorize_url)


class Logout(View):
    def get(self, request):
        logout(request)
        return redirect('/')


def dropbox_auth_finish(request):
    try:
        oauth_result = get_dropbox_auth_flow(request.session).finish(request.GET)
        dbx = dropbox.Dropbox(oauth_result.access_token)
        from django.contrib.auth.models import User
        get_user = dbx.users_get_current_account()
        defaults = {
            'password': oauth_result.access_token,
            'email': get_user.email,
            'first_name': get_user.name.given_name,
            'last_name': get_user.name.surname
        }
        user, created = User.objects.update_or_create(username=oauth_result.account_id, defaults=defaults)
        login(request, user)
        request.session['dropbox'] = {
            'token': oauth_result.access_token,
            'name': get_user.name.display_name,
            'photo': get_user.profile_photo_url,
        }
    except BadRequestException as e:
        print("Error 403  %s" % (e,))
    except BadStateException:
        redirect("/dropbox-auth-start")
    except CsrfException as e:
        print("Error 403  %s" % (e,))
    except NotApprovedException as e:
        print("Error not approved %s" % (e,))
    except ProviderException as e:
        print("Error 403  %s" % (e,))


def get_dropbox_auth_flow(web_app_session):
    return DropboxOAuth2Flow(settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET, settings.DROPBOX_REDIRECT_URI,
                             web_app_session, "dropbox-auth-csrf-token")
