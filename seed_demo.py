#!/usr/bin/env python
"""
AgriBazaar — seed_demo.py
Run once after migrations to create demo users and sample listings.

Usage:
    python manage.py shell < seed_demo.py
  or:
    python seed_demo.py   (if run from project root with Django configured)
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agribazaar.settings')
django.setup()

from django.contrib.auth.hashers import make_password

from core.models import User, Listing, Order, Review
from django.utils import timezone

print("🌱 Seeding demo data...")

# ── DEMO USERS ────────────────────────────────────────────────
seller, _ = User.objects.update_or_create(
    email='seller@demo.com',
    defaults=dict(
        name='Ahmed Khan', pw=make_password('demo123'), phone='03211234567',
        city='Lahore', role='seller',
        verified_phone=True, verified_email=True,
        cnic='35202-1234567-1', cnic_name='Ahmed Khan',
        bank_iban='PK36HABB0000001123456702', bank_name='HBL',
        bank_title='Ahmed Khan Agri',
        jazzcash='03211234567', easypaisa='03211234567',
    )
)
print(f"  ✅ Seller: {seller.email}")

buyer, _ = User.objects.update_or_create(
    email='buyer@demo.com',
    defaults=dict(
        name='Sara Malik', pw=make_password('demo123'), phone='03339876543',
        city='Karachi', role='buyer',
        verified_phone=True, verified_email=True,
    )
)
print(f"  ✅ Buyer:  {buyer.email}")

# ── DEMO LISTINGS ─────────────────────────────────────────────
demo_listings = [
    dict(crop='Tomato',  city='Lahore',     price=85,  qty=1000, market='Hall Road Mandi',       desc='Grade A tomatoes, freshly picked. Direct farm supply.'),
    dict(crop='Potato',  city='Lahore',     price=60,  qty=2000, market='Badami Bagh Mandi',     desc='White potatoes, washed and sorted. 50kg bags available.'),
    dict(crop='Onion',   city='Multan',     price=55,  qty=1500, market='Hussain Agahi Mandi',   desc='Red onions, dry skin. Long shelf life.'),
    dict(crop='Garlic',  city='Islamabad',  price=220, qty=500,  market='I-9 Sabzi Mandi',       desc='Local garlic, strong flavour. Bulk pricing available.'),
    dict(crop='Carrot',  city='Rawalpindi', price=70,  qty=800,  market='Raja Bazaar Mandi',     desc='Fresh orange carrots, washed. Good for juicing.'),
    dict(crop='Peas',    city='Sialkot',    price=130, qty=600,  market='Model Town Mandi',      desc='Green peas, sweet and tender. Seasonal crop.'),
    dict(crop='Cucumber',city='Karachi',    price=65,  qty=1200, market='Shershah Sabzi Mandi',  desc='Crisp cucumbers from Balochistan. Daily stock.'),
    dict(crop='Brinjal', city='Faislabad',  price=50,  qty=900,  market='Kachehri Bazaar Mandi', desc='Dark purple brinjal, firm texture.'),
]

created_listings = []
for d in demo_listings:
    l, created = Listing.objects.get_or_create(
        seller=seller, crop=d['crop'], city=d['city'],
        defaults=dict(price=d['price'], qty=d['qty'], market=d['market'], desc=d['desc'], qty_sold=0)
    )
    created_listings.append(l)
    if created:
        print(f"  📦 Listing: {l.crop} – {l.city}")

# ── DEMO ORDER + REVIEW ───────────────────────────────────────
if created_listings:
    first_listing = created_listings[0]
    order, created = Order.objects.get_or_create(
        id='AGR-DEMO001',
        defaults=dict(
            listing=first_listing, buyer=buyer, seller=seller,
            crop=first_listing.crop, city=first_listing.city,
            market=first_listing.market, price=first_listing.price,
            qty=100, total=100 * first_listing.price,
            pay_method='cod', status='delivered',
            buyer_name=buyer.name, buyer_email=buyer.email,
            seller_name=seller.name,
        )
    )
    if created:
        # Update qty_sold
        first_listing.qty_sold += 100
        first_listing.save()
        print(f"  🛒 Demo order created: {order.id}")

    # Demo review
    review, created = Review.objects.get_or_create(
        listing=first_listing, reviewer=buyer,
        defaults=dict(rating=5, comment='Excellent quality tomatoes! Fast delivery and great price. Highly recommend Ahmed Khan.', order=order)
    )
    if created:
        print(f"  ⭐ Demo review created")

print("\n✅ Done! Demo credentials:")
print("   Seller: seller@demo.com / demo123")
print("   Buyer:  buyer@demo.com  / demo123")
