from __future__ import unicode_literals
try:
    # For Python 3.0 and later
    from urllib.error import URLError
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import URLError
    from urllib import urlencode
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.http import JsonResponse
import requests
import logging

from .forms import TalerPaymentForm
from .. import PaymentError, PaymentStatus, RedirectNeeded
from ..core import BasicProvider
import re
import json
from random import randint
from datetime import datetime


logger = logging.getLogger(__name__)
CURRENCY = "KUDOS"
BACKEND_URL = "http://backend.demo.taler.net/"

def string_to_amount(fmt):
    pattern = re.compile("^[0-9]+\.[0-9]+:[A-Z]+$")
    assert(pattern.match(fmt))
    split = fmt.split(":")
    num = split[0]
    currency = split[1]
    split = num.split(".")
    value = int(split[0])
    fraction = float("0." + split[1]) * FRACTION
    return dict(value=value, fraction=int(fraction), currency=currency)

class TalerProvider(BasicProvider):
    '''
    Gnu Taler payment provider
    '''


    def get_form(self, payment, data=None):
        kwargs = {
            'data': data,
            'payment': payment,
            'provider': self,
            'action': '',
            'hidden_inputs': False}
        return TalerPaymentForm(**kwargs)




    def process_data(self, payment, request):
        if payment.status == PaymentStatus.WAITING:
            payment.change_status(PaymentStatus.INPUT)

        url = urljoin(BACKEND_URL, "proposal")
        r = requests.post(url, json=dict(order=order))
        if r.status_code != 200:
            logger.error("failed to POST to '%s'", url)
            return r.text, r.status_code
        proposal_resp = r.json()
        return JsonResponse(**proposal_resp)
    def capture(self, payment, amount=None):
        return
    def release(self, payment):
        return
    def refund(self, payment, amount=None):
        return
