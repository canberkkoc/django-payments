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
from django.shortcuts import redirect
import requests
import logging

from .forms import TalerPaymentForm
from .. import PaymentError, PaymentStatus, RedirectNeeded, PaymentRequired
from ..core import BasicProvider
import re
import json
from random import randint
from datetime import datetime


logger = logging.getLogger(__name__)
CURRENCY = "KUDOS"
BACKEND_URL = "http://backend.demo.taler.net/"

FRACTION = 100000000


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

    def get_action(self, payment):
        response = HttpResponse(status=402)
        response["X-Taler-Contract-Url"] = payment.get_process_url()
        raise PaymentRequired("Payment Required", response)

    def get_hidden_fields(self, payment):
        return {}

    def process_data(self, payment, request):
        if payment.status == PaymentStatus.WAITING:
            payment.change_status(PaymentStatus.INPUT)

        DONATION = string_to_amount("1.00:%s" % CURRENCY)
        MAX_FEE = string_to_amount("0.05:%s" % CURRENCY)

        order = dict(
            order_id=payment.pk,
            nonce=request.GET.get("nonce"),
            amount=DONATION,
            max_fee=MAX_FEE,
            products=[
                dict(
                    description="Donation",
                    quantity=1,
                    product_id=0,
                    price=DONATION,
                ),
            ],
            fulfillment_url=payment.get_success_url(),
            pay_url=payment.get_failure_url(),
            merchant=dict(
                instance="tutorial",
                address="nowhere",
                name="Donation tutorial",
                jurisdiction="none",
            ),
        )

        proposal_url = BACKEND_URL + "proposal"

        r = requests.post(proposal_url, json=dict(order=order))
        if r.status_code != 200:
            logger.error("failed to POST to '%s'", url)
            return r.text, r.status_code
        proposal_resp = r.json()

        return JsonResponse(proposal_resp)

    def refund(self, payment, amount=None):
        return
