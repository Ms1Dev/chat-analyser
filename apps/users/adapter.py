from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        max_users = getattr(settings, 'MAX_FREE_USERS', None)
        if max_users is not None:
            from django.contrib.auth import get_user_model
            if get_user_model().objects.count() >= max_users:
                return False
        return super().is_open_for_signup(request)
