from __future__ import unicode_literals
from django import forms

from ..forms import PaymentForm
from .. import FraudStatus, PaymentStatus



class TalerPaymentForm(PaymentForm):
    DONATION = string_to_amount("1.00:%s" % CURRENCY)
    MAX_FEE = string_to_amount("0.05:%s" % CURRENCY)
    ORDER_ID = "tutorial-%X-%s" % (randint(0, 0xFFFFFFFF), datetime.today().strftime("%H_%M_%S"))
    order = dict(
        order_id=ORDER_ID,
        nonce=request.GET.get("nonce"),
        amount=DONATION,
        max_fee=MAX_FEE,
        products=[
            dict(
                description="Love",
                quantity=1,
                product_id=0,
                price=DONATION,
            ),
        ],
        fulfillment_url=make_url("/fulfillment", ("order_id", ORDER_ID)),
        pay_url=make_url("/pay"),
        merchant=dict(
            instance="tutorial",
            address="nowhere",
            name="Donation 33",
            jurisdiction="none",
        ),
    )
