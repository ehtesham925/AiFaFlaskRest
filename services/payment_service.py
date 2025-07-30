import stripe
import os
from flask import current_app

class PaymentService:
    def __init__(self):
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        self.webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        self.domain = self._get_domain()
    
    def _get_domain(self):
        """Get the domain for redirect URLs"""
        # Check if running on Replit
        if os.environ.get('REPLIT_DEPLOYMENT'):
            return f"https://{os.environ.get('REPLIT_DEV_DOMAIN')}"
        elif os.environ.get('REPLIT_DOMAINS'):
            return f"https://{os.environ.get('REPLIT_DOMAINS').split(',')[0]}"
        else:
            return os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    
    def create_checkout_session(self, course, user, payment_id):
        """Create a Stripe checkout session for course payment"""
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': course.currency.lower(),
                            'product_data': {
                                'name': course.title,
                                'description': course.short_description or course.description[:100],
                                'images': [course.thumbnail] if course.thumbnail else [],
                            },
                            'unit_amount': int(float(course.price) * 100),  # Convert to cents
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=f'{self.domain}/api/v1/payments/success/{payment_id}',
                cancel_url=f'{self.domain}/api/v1/payments/cancel/{payment_id}',
                customer_email=user.email,
                client_reference_id=str(payment_id),
                metadata={
                    'payment_id': str(payment_id),
                    'user_id': str(user.id),
                    'course_id': str(course.id),
                    'user_email': user.email,
                },
                automatic_tax={'enabled': False},  # Set to True if you want automatic tax calculation
                allow_promotion_codes=True,
            )
            
            return checkout_session
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        except Exception as e:
            raise Exception(f"Payment service error: {str(e)}")
    
    def get_checkout_session(self, session_id):
        """Retrieve a checkout session by ID"""
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def verify_webhook(self, payload, sig_header):
        """Verify Stripe webhook signature and return event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise Exception("Invalid signature")
    
    def create_payment_intent(self, amount, currency, customer_id=None, metadata=None):
        """Create a payment intent for manual payment processing"""
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True},
            )
            return payment_intent
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_customer(self, user):
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={
                    'user_id': str(user.id),
                }
            )
            return customer
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_refund(self, payment_intent_id, amount=None, reason=None):
        """Create a refund for a payment"""
        try:
            refund_params = {
                'payment_intent': payment_intent_id,
            }
            
            if amount:
                refund_params['amount'] = int(amount * 100)  # Convert to cents
            
            if reason:
                refund_params['reason'] = reason
            
            refund = stripe.Refund.create(**refund_params)
            return refund
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def get_payment_intent(self, payment_intent_id):
        """Retrieve a payment intent by ID"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def list_customer_payments(self, customer_id, limit=10):
        """List payments for a customer"""
        try:
            payments = stripe.PaymentIntent.list(
                customer=customer_id,
                limit=limit
            )
            return payments
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_subscription(self, customer_id, price_id, trial_period_days=None):
        """Create a subscription for recurring payments"""
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'payment_behavior': 'default_incomplete',
                'expand': ['latest_invoice.payment_intent'],
            }
            
            if trial_period_days:
                subscription_params['trial_period_days'] = trial_period_days
            
            subscription = stripe.Subscription.create(**subscription_params)
            return subscription
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def cancel_subscription(self, subscription_id):
        """Cancel a subscription"""
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_price(self, product_id, amount, currency, interval=None):
        """Create a price for a product"""
        try:
            price_params = {
                'product': product_id,
                'unit_amount': int(amount * 100),  # Convert to cents
                'currency': currency.lower(),
            }
            
            if interval:  # For subscriptions
                price_params['recurring'] = {'interval': interval}
            
            price = stripe.Price.create(**price_params)
            return price
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def create_product(self, name, description=None, images=None):
        """Create a product"""
        try:
            product_params = {
                'name': name,
            }
            
            if description:
                product_params['description'] = description
            
            if images:
                product_params['images'] = images
            
            product = stripe.Product.create(**product_params)
            return product
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def get_balance(self):
        """Get account balance"""
        try:
            balance = stripe.Balance.retrieve()
            return balance
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
    
    def list_charges(self, limit=10, customer=None):
        """List charges"""
        try:
            params = {'limit': limit}
            if customer:
                params['customer'] = customer
            
            charges = stripe.Charge.list(**params)
            return charges
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
