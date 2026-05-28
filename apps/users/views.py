from django.shortcuts import render
from allauth.account.views import PasswordChangeView


class PasswordChangeOverride(PasswordChangeView):
    template_name = "account/password_set.html"
