import typing
from django.urls import path
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import reverse
from django.views.decorators.csrf import csrf_exempt
from waveapps.app import WaveStorageInterface as StorageInterface, WaveOauth
from waveapps import WaveException, sync_to_async, async_to_sync
from . import settings as django_settings


class DjangoStorageInterface(StorageInterface):
    @property
    def klass(self):
        storage_klass = django_settings.WAVEAPPS_STORAGE_CLASS
        if not storage_klass:
            raise WaveException("Missing storage class in settings")
        klass = storage_klass()
        return klass

    @sync_to_async
    def get_token(self, view_url):
        result: typing.Optional[typing.Any] = self.klass.get_token()
        if result:
            self.userId = result.userId
            self.businessId = result.businessId
            self.access_token = result.access_token
            self.expires_in = result.expires_in
            self.refresh_token = result.refresh_token
            self.date_added = result.date_added
        return self

    @sync_to_async
    def save_token(self, **token):
        super().save_token(**token)
        businessId = token.pop("businessId", None)
        if not businessId:
            businessId = self.businessId
        self.klass.save_token(businessId=businessId, **token)


def get_redirect_uri(request):
    url = request.build_absolute_uri(reverse("waveapps:code"))
    if not django_settings.DEBUG:
        url = url.replace("http://", "https://")
    return url


credentials = {
    "client_id": django_settings.WAVEAPPS_CLIENT_ID,
    "client_secret": django_settings.WAVEAPPS_CLIENT_SECRET,
    "storage_interface": DjangoStorageInterface(),
    "state": django_settings.WAVEAPPS_STATE,
    "scopes": django_settings.WAVEAPPS_SCOPES,
}
if django_settings.WAVEAPPS_BUSINESS_ID:
    credentials["businessId"] = django_settings.WAVEAPPS_BUSINESS_ID


def waveapps_auth_response(request):
    hub = WaveOauth(redirect_uri=get_redirect_uri(request), **credentials)
    try:
        response = async_to_sync(hub.on_auth_response)(**request.GET.dict())
    except WaveException:
        return HttpResponseBadRequest("This is a bad request")
    return JsonResponse(response)


def wave_authorize(request):
    hub = WaveOauth(redirect_uri=get_redirect_uri(request), **credentials)
    return HttpResponse(hub.auth_button())


urlpatterns = [
    path("auth-response", waveapps_auth_response, name="code"),
    path("authorize", wave_authorize, name="authorize"),
]
