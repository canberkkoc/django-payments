'''
Copyright (c) 2017, Canberk Koç
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the name of the Canberk Koç nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY CANBERK KOÇ ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL CANBERK KOÇ BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

from __future__ import unicode_literals
try:
    # For Python 3.0 and later
    from urllib.error import URLError
    from urllib.parse import urlencode
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import URLError
    from urllib import urlencode

from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
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

    def __init__(self, backend_url, instance, address, name, jurisdiction):
        self._backend_url = backend_url
        self._instance = instance
        self._address = address
        self._name = name
        self._jurisdiction = jurisdiction
        super(TalerProvider, self)

    def get_action(self, payment):
        response = HttpResponse(status=402)
        response["X-Taler-Contract-Url"] = payment.get_process_url()
        raise PaymentRequired("Payment Required", response)

    def get_hidden_fields(self, payment):
        return {}

    def process_data(self, payment, request):
        if payment.status == PaymentStatus.INPUT:
            deposit_permission = request.GET.get('paid', False)
            if deposit_permission is None:
                e = JsonResponse(error="no json in body")
                return e, 400
            payurl= self._backend_url+ "pay"
            r = requests.post(payurl, json=deposit_permission)
            if 200 != r.status_code:
                logger.error("Backend said, status code: %d, object: %s" % (r.status_code, r.text))
                return r.text, r.status_code
            contract_terms = r.json()["contract_terms"]
            request.session["paid"] = True
            request.session["order_id"] = contract_terms["order_id"]
            payment.change_status(PaymentStatus.CONFIRMED)
            return JsonResponse(r.json()), 200
        if payment.status == PaymentStatus.WAITING:
            payment.change_status(PaymentStatus.INPUT)
            total_amount = string_to_amount("%s:%s" % (payment.total, payment.currency))
            max_fee = string_to_amount("0.05:%s" % payment.currency)
            order = dict(
                order_id=payment.transaction_id,
                nonce=request.GET.get("nonce"),
                amount=total_amount,
                max_fee=max_fee,
                products=[
                    dict(
                        description=payment.description,
                        quantity=1,
                        product_id=0,
                        price=total_amount,
                    ),
                ],
                pay_url=payment.get_success_url(),
                fulfillment_url=self.get_return_url(payment),
                merchant=dict(
                    instance=self._instance,
                    address=self._address,
                    name=self._name,
                    jurisdiction=self._jurisdiction,
                ),
            )
            proposal_url = self._backend_url + "proposal"
            r = requests.post(proposal_url, json=dict(order=order))
            if r.status_code != 200:
                logger.error("failed to POST to '%s'", url)
                return r.text, r.status_code
            proposal_resp = r.json()
            return JsonResponse(proposal_resp)

    def refund(self, payment, amount=None):
        return
