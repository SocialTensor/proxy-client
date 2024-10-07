import stripe
import os
from utils.data_types import StripePay
from fastapi import Request
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripeService:
    def __init__(self):
        return

    async def create_payment_intent(data: StripePay):
        try:
            intent = stripe.PaymentIntent.create(
                amount=data.price*100,
                currency='usd',
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            return intent['client_secret']
        except Exception as e:
            return "error"