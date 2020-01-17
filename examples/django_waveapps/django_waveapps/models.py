from django.db import models

from django.utils import timezone


class WaveappsStorage(models.Model):
    token = models.TextField()
    businessId = models.CharField(max_length=200, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    @property
    def raw_token(self):
        return json.loads(self.token)

    @property
    def access_token(self):
        return self.raw_token["access_token"]

    @property
    def refresh_token(self):
        return self.raw_token["refresh_token"]

    @property
    def expires_in(self):
        return self.raw_token["expires_in"]

    @property
    def userId(self):
        return self.raw_token["userId"]

    @classmethod
    def get_token(cls):
        return cls.objects.first()

    @classmethod
    def save_token(cls, businessId, **kwargs):
        cls.objects.all().delete()
        return cls.objects.create(token=json.dumps(kwargs), businessId=businessId)
