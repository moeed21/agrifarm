"""
AgriBazaar — models.py
Full database-backed models for users, listings, orders, reviews.
"""
from django.db import models
from django.utils import timezone
import uuid


class User(models.Model):
    ROLE_CHOICES = [('seller', 'Seller'), ('buyer', 'Buyer')]

    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name        = models.CharField(max_length=150)
    email       = models.EmailField(unique=True)
    pw          = models.CharField(max_length=256)
    phone       = models.CharField(max_length=20, blank=True)
    city        = models.CharField(max_length=80, blank=True)
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default='buyer')
    is_admin    = models.BooleanField(default=False)

    verified_phone = models.BooleanField(default=False)
    verified_email = models.BooleanField(default=False)

    # Seller payment details
    cnic        = models.CharField(max_length=20, blank=True)
    cnic_name   = models.CharField(max_length=150, blank=True)
    bank_iban   = models.CharField(max_length=40, blank=True)
    bank_name   = models.CharField(max_length=80, blank=True)
    bank_title  = models.CharField(max_length=150, blank=True)
    jazzcash    = models.CharField(max_length=20, blank=True)
    easypaisa   = models.CharField(max_length=20, blank=True)

    # CNIC photo verification
    CNIC_VERIFY_CHOICES = [
        ('none',     'Not Submitted'),
        ('pending',  'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    cnic_front    = models.ImageField(upload_to='cnic/', null=True, blank=True)
    cnic_back     = models.ImageField(upload_to='cnic/', null=True, blank=True)
    cnic_verified = models.CharField(
        max_length=10, choices=CNIC_VERIFY_CHOICES, default='none'
    )

    avatar      = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ab_user'

    def __str__(self):
        return f"{self.name} ({self.role})"

    def to_dict(self):
        return {
            'id': str(self.id), 'name': self.name, 'email': self.email,
            'phone': self.phone, 'city': self.city,
            'role': self.role, 'verified_phone': self.verified_phone,
            'verified_email': self.verified_email, 'cnic': self.cnic,
            'cnic_name': self.cnic_name, 'bank_iban': self.bank_iban,
            'bank_name': self.bank_name, 'bank_title': self.bank_title,
            'jazzcash': self.jazzcash, 'easypaisa': self.easypaisa,
            'avatar': self.avatar.url if self.avatar else None,
            'cnic_front': self.cnic_front.url if self.cnic_front else None,
            'cnic_back': self.cnic_back.url if self.cnic_back else None,
            'cnic_verified': self.cnic_verified,
            'is_admin': self.is_admin,
        }


class Listing(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('sold', 'Sold'), ('inactive', 'Inactive')]

    seller      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    crop        = models.CharField(max_length=50)
    crop_type   = models.CharField(max_length=30, blank=True, default='')  # e.g. Vegetables, Fruits
    city        = models.CharField(max_length=80)
    market      = models.CharField(max_length=150, blank=True)
    price       = models.PositiveIntegerField()
    qty         = models.PositiveIntegerField()
    qty_sold    = models.PositiveIntegerField(default=0)
    desc        = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    image1      = models.ImageField(upload_to='listings/', null=True, blank=True)
    image2      = models.ImageField(upload_to='listings/', null=True, blank=True)
    image3      = models.ImageField(upload_to='listings/', null=True, blank=True)
    image4      = models.ImageField(upload_to='listings/', null=True, blank=True)

    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = 'ab_listing'
        ordering  = ['-created_at']

    def __str__(self):
        return f"{self.crop} - {self.city} by {self.seller.name}"

    @property
    def primary_image(self):
        for f in [self.image1, self.image2, self.image3, self.image4]:
            if f:
                return f.url
        return None

    @property
    def all_images(self):
        return [f.url for f in [self.image1, self.image2, self.image3, self.image4] if f]

    @property
    def avg_rating(self):
        qs = self.reviews.all()
        if not qs.exists():
            return None
        return round(sum(r.rating for r in qs) / qs.count(), 1)

    @property
    def review_count(self):
        return self.reviews.count()

    def to_dict(self):
        return {
            'id': self.pk, 'crop': self.crop, 'city': self.city,
            'market': self.market, 'price': self.price, 'qty': self.qty,
            'qty_sold': self.qty_sold, 'desc': self.desc, 'status': self.status,
            'seller': self.seller.name, 'seller_id': str(self.seller_id),
            'phone': self.seller.phone, 'sid': str(self.seller_id),
            'date': str(self.created_at.date()),
            'image': self.primary_image,
            'all_images': self.all_images,
            'avg_rating': self.avg_rating,
            'review_count': self.review_count,
            'min_price': self.price, 'max_price': self.price, 'change_7d': 0,
        }


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending','Pending'),('confirmed','Confirmed'),
        ('delivered','Delivered'),('cancelled','Cancelled'),
    ]
    PAY_CHOICES = [
        ('cod','Cash on Delivery'),('jazzcash','JazzCash'),
        ('easypaisa','EasyPaisa'),('bank','Bank Transfer'),
    ]

    id          = models.CharField(primary_key=True, max_length=30)
    listing     = models.ForeignKey(Listing, on_delete=models.SET_NULL, null=True, related_name='orders')
    buyer       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    seller      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales')

    crop        = models.CharField(max_length=50)
    city        = models.CharField(max_length=80)
    market      = models.CharField(max_length=150, blank=True)
    price       = models.PositiveIntegerField()
    qty         = models.PositiveIntegerField()
    total       = models.PositiveIntegerField()
    pay_method  = models.CharField(max_length=20, choices=PAY_CHOICES, default='cod')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    buyer_name  = models.CharField(max_length=150, blank=True)
    buyer_email = models.EmailField(blank=True)
    seller_name = models.CharField(max_length=150, blank=True)

    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ab_order'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.id} - {self.crop} {self.qty}kg"

    def to_dict(self):
        return {
            'id': self.id, 'crop': self.crop, 'city': self.city,
            'market': self.market, 'price': self.price, 'qty': self.qty,
            'total': self.total, 'pay_method': self.pay_method,
            'status': self.status, 'buyer': self.buyer_name,
            'buyer_email': self.buyer_email, 'seller': self.seller_name,
            'date': str(self.created_at.date()),
            'listing_id': self.listing_id,
        }


class Review(models.Model):
    listing     = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    reviewer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    order       = models.OneToOneField(Order, on_delete=models.SET_NULL, null=True, blank=True)
    rating      = models.PositiveSmallIntegerField()  # 1-5
    comment     = models.TextField(blank=True)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ab_review'
        ordering = ['-created_at']
        unique_together = [('listing', 'reviewer')]

    def __str__(self):
        return f"{self.reviewer.name} -> {self.listing} ({self.rating} stars)"
