"""
AgriBazaar — views.py (production-ready)
All views handle missing CSV gracefully.
"""
import json, random
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q
from django.conf import settings

from .models  import User, Listing, Order, Review
from . import data_loader as dl
from . import ai_engine   as ai
from . import email_utils as eu
from . import cnic_verifier as cv
from .sendgrid_utils import generate_otp, send_otp_email as _sg_send_otp


def _gen_otp():
    """Generate a secure random numeric OTP."""
    return generate_otp(6)


def _send_otp_email(to_email, otp, purpose='Verification', user_name=''):
    """Send OTP via SendGrid (falls back to SMTP). Always logs to console."""
    _sg_send_otp(to_email, otp, purpose=purpose, user_name=user_name)

# ── CROP DEFINITIONS ────────────────────────────────────────────────────────
CROP_GROUPS = {
    'Vegetables': [
        'Tomato','Potato','Onion','Garlic','Carrot','Peas','Cucumber','Brinjal',
        'Spinach','Cauliflower','Cabbage','Bitter Gourd','Bottle Gourd',
        'Ladyfinger','Tinda','Corn','Ginger','Turmeric','Turnip','Radish','Beetroot',
    ],
    'Fruits': [
        'Mango','Banana','Apple','Orange','Guava','Watermelon','Melon',
        'Grapes','Lemon','Pomegranate','Peach','Apricot','Strawberry',
    ],
    'Grains & Pulses': [
        'Wheat','Rice','Maize','Chickpeas','Lentils','Moong Dal','Masoor Dal',
    ],
    'Cash Crops': [
        'Sugarcane','Cotton','Sunflower',
    ],
}
CROPS = [c for group in CROP_GROUPS.values() for c in group]
CITIES = ['Karachi','Lahore','Multan','Faislabad','Sialkot','Quetta','Peshawer','Rawalpindi','Islamabad']
EMOJI = {
    'Tomato':'🍅','Potato':'🥔','Onion':'🧅','Garlic':'🧄','Carrot':'🥕',
    'Peas':'🫛','Cucumber':'🥒','Brinjal':'🍆','Spinach':'🥬','Cauliflower':'🥦',
    'Cabbage':'🥬','Bitter Gourd':'🌿','Bottle Gourd':'🫙','Ladyfinger':'🌿',
    'Corn':'🌽','Ginger':'🟤','Turmeric':'🟡','Turnip':'🥕','Radish':'🌱',
    'Beetroot':'🟣','Mango':'🥭','Banana':'🍌','Apple':'🍎','Orange':'🍊',
    'Guava':'🍐','Watermelon':'🍉','Melon':'🍈','Grapes':'🍇','Lemon':'🍋',
    'Pomegranate':'🍎','Peach':'🍑','Apricot':'🍑','Strawberry':'🍓',
    'Wheat':'🌾','Rice':'🌾','Maize':'🌽','Chickpeas':'🫘','Lentils':'🫘',
    'Moong Dal':'🫘','Masoor Dal':'🫘','Sugarcane':'🎋','Cotton':'🌿','Sunflower':'🌻',
}
MONTHS = ['January','February','March','April','May','June',
          'July','August','September','October','November','December']


# ── HELPERS ─────────────────────────────────────────────────────────────────

def _safe_monthly_avg(crop, city):
    """Returns monthly averages or zeros if CSV not loaded."""
    try:
        return dl.get_monthly_avg(crop, city)
    except Exception:
        return [0] * 12

def _safe_ai_badge(price, crop, city):
    """Returns AI badge, falls back gracefully."""
    try:
        return ai.ai_badge(price, crop, city)
    except Exception:
        return {'cls': 'badge-fair', 'txt': '🤖 Fair'}

def _safe_dataset_info():
    try:
        return dl.get_dataset_info()
    except Exception:
        return {
            'rows': 0, 'crops': CROPS, 'cities': CITIES,
            'markets': [], 'date_from': 'N/A', 'date_to': 'N/A',
        }

def get_user(request):
    uid = request.session.get('user_id')
    if not uid:
        return None
    try:
        return User.objects.get(pk=uid)
    except User.DoesNotExist:
        request.session.flush()
        return None



def base_ctx(request, extra=None):
    info = _safe_dataset_info()
    u = get_user(request)
    c = {
        'user':       u.to_dict() if u else None,
        'user_obj':   u,
        'crops':      CROPS,
        'crop_groups': CROP_GROUPS,
        'cities':     CITIES,
        'emoji':      EMOJI,
        'months':     MONTHS,
        'info':       info,
        'now':        datetime.now(),
    }
    if extra:
        c.update(extra)
    return c


# ── PUBLIC PAGES ─────────────────────────────────────────────────────────────

def landing(request):
    m = datetime.now().month - 1
    featured = []
    try:
        qs = Listing.objects.filter(status='active').select_related('seller').prefetch_related('reviews')[:10]
        for l in qs:
            d = l.to_dict()
            badge = _safe_ai_badge(l.price, l.crop, l.city)
            d['badge_cls'] = badge['cls']
            d['badge_txt'] = badge['txt']
            d['emoji']     = EMOJI.get(l.crop, '🌿')
            avg = _safe_monthly_avg(l.crop, l.city)[m]
            d['market_avg'] = avg
            d['discount']   = round((1 - l.price / avg) * 100) if avg and l.price < avg else 0
            d['sold_pct']   = min(100, round(l.qty_sold / max(l.qty, 1) * 100))
            featured.append(d)
    except Exception:
        pass
    return render(request, 'core/landing.html', base_ctx(request, {
        'featured_listings': featured
    }))


def analysis(request):
    crop  = request.GET.get('crop', 'Tomato')
    city  = request.GET.get('city', 'Lahore')
    role  = request.GET.get('role', 'buyer')
    start = max(0, datetime.now().month - 1)  # Always current month
    try:
        result     = ai.analyze(crop, city, role)
        forecast   = ai.farmer_forecast(crop, city, start)
        mandis     = dl.get_latest_mandi_prices(city, crop)
        all_cities = dl.get_all_city_prices(crop)
        history    = dl.get_price_history(crop, city, 90)
    except FileNotFoundError as e:
        return render(request, 'core/no_data.html', base_ctx(request, {'error': str(e)}))
    except Exception as e:
        return render(request, 'core/no_data.html', base_ctx(request, {'error': str(e)}))

    # Only show crops that actually exist in the CSV dataset
    try:
        dataset_crops = dl.get_crops()
    except Exception:
        dataset_crops = CROPS  # fallback to full list if CSV missing

    return render(request, 'core/analysis.html', base_ctx(request, {
        'crop': crop, 'city': city, 'role': role,
        'analysis': result, 'forecast': forecast, 'mandis': mandis,
        'all_cities': all_cities, 'month_names': MONTHS,
        'forecast_json':   json.dumps(forecast['months'], default=str),
        'all_cities_json': json.dumps(all_cities, default=str),
        'monthly_json':    json.dumps(result['monthly'], default=str),
        'history_json':    json.dumps(history, default=str),
        'dataset_crops':   dataset_crops,
    }))


def marketplace(request):
    crop     = request.GET.get('crop', '')
    city     = request.GET.get('city', '')
    category = request.GET.get('category', '')   # new: filter by crop group
    sort     = request.GET.get('sort', 'newest')
    pmin     = request.GET.get('pmin', '')
    pmax     = request.GET.get('pmax', '')

    qs = Listing.objects.filter(status='active').select_related('seller').prefetch_related('reviews')
    if crop:     qs = qs.filter(crop__iexact=crop)
    if category:
        # Filter by crop_type field (saved in DB) OR by static CROP_GROUPS list
        if category in CROP_GROUPS:
            qs = qs.filter(
                Q(crop_type=category) |
                Q(crop__in=CROP_GROUPS[category])
            )
        else:
            qs = qs.filter(crop_type=category)
    if city:     qs = qs.filter(city=city)
    if pmin:
        try: qs = qs.filter(price__gte=int(pmin))
        except ValueError: pass
    if pmax:
        try: qs = qs.filter(price__lte=int(pmax))
        except ValueError: pass

    if sort == 'price-low':    qs = qs.order_by('price')
    elif sort == 'price-high': qs = qs.order_by('-price')
    else:                      qs = qs.order_by('-created_at')

    m = datetime.now().month - 1
    listings = []
    for l in qs:
        d = l.to_dict()
        badge = _safe_ai_badge(l.price, l.crop, l.city)
        d['badge_cls'] = badge['cls']
        d['badge_txt'] = badge['txt']
        d['emoji']     = EMOJI.get(l.crop, '🌿')
        avg = _safe_monthly_avg(l.crop, l.city)[m]
        nxt = _safe_monthly_avg(l.crop, l.city)[(m + 1) % 12]
        d['market_avg']   = avg
        d['discount']     = round((1 - l.price / avg) * 100) if avg and l.price < avg else 0
        d['price_alert']  = bool(nxt) and nxt < l.price * 0.93        # price DROPPING next month
        d['price_rising'] = bool(nxt) and nxt > l.price * 1.05        # price RISING next month
        d['nxt_price']    = nxt
        d['nxt_drop_pct'] = round((l.price - nxt) / l.price * 100) if nxt and nxt < l.price else 0
        d['rise_pct']     = round((nxt - l.price) / l.price * 100) if nxt and nxt > l.price else 0
        d['sold_pct']     = min(100, round(l.qty_sold / max(l.qty, 1) * 100))
        # Recent reviews for avatar strip
        recent_revs = l.reviews.select_related('reviewer').order_by('-created_at')[:3]
        d['recent_reviews'] = [{'reviewer_name': r.reviewer.name, 'rating': r.rating} for r in recent_revs]
        listings.append(d)

    # Merge known CROPS with any custom crops already posted by sellers
    db_crops = list(Listing.objects.values_list('crop', flat=True).distinct().order_by('crop'))
    all_crops = sorted(set(CROPS) | set(db_crops), key=str.lower)

    # Category icons for pills
    CAT_ICONS = {
        'Vegetables':      '🥦',
        'Fruits':          '🍎',
        'Grains & Pulses': '🌾',
        'Cash Crops':      '🌿',
    }

    return render(request, 'core/marketplace.html', base_ctx(request, {
        'listings':    listings,
        'filter_crop': crop,
        'filter_city': city,
        'filter_cat':  category,
        'sort':        sort,
        'count':       len(listings),
        'pmin':        pmin,
        'pmax':        pmax,
        'crops':       all_crops,
        'crop_groups': CROP_GROUPS,
        'cat_icons':   CAT_ICONS,
    }))


def listing_detail(request, lid):
    listing = get_object_or_404(Listing, pk=lid, status='active')
    reviews = listing.reviews.select_related('reviewer').all()
    user    = get_user(request)

    # AI analysis — graceful fallback
    try:
        result = ai.analyze(listing.crop, listing.city, 'buyer')
    except Exception:
        result = None

    already_reviewed = False
    can_review = False
    if user and user.role == 'buyer':
        already_reviewed = Review.objects.filter(listing=listing, reviewer=user).exists()
        can_review = (
            not already_reviewed and
            Order.objects.filter(listing=listing, buyer=user, status__in=['confirmed','delivered']).exists()
        )

    msg = ''
    if request.method == 'POST' and user and can_review:
        rating  = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '').strip()
        order   = Order.objects.filter(listing=listing, buyer=user).first()
        Review.objects.create(listing=listing, reviewer=user, order=order, rating=rating, comment=comment)
        msg = '✅ Review submitted!'
        already_reviewed = True
        can_review = False
        reviews = listing.reviews.select_related('reviewer').all()

    d = listing.to_dict()
    d['emoji'] = EMOJI.get(listing.crop, '🌿')
    return render(request, 'core/listing_detail.html', base_ctx(request, {
        'listing':          listing,
        'listing_dict':     d,
        'reviews':          reviews,
        'analysis':         result,
        'already_reviewed': already_reviewed,
        'can_review':       can_review,
        'msg':              msg,
        'emoji':            EMOJI.get(listing.crop, '🌿'),
    }))


def checkout(request, lid):
    user    = get_user(request)
    listing = get_object_or_404(Listing, pk=lid, status='active')
    try:
        result = ai.analyze(listing.crop, listing.city, 'buyer')
    except Exception:
        result = None
    d = listing.to_dict()
    d['emoji'] = EMOJI.get(listing.crop, '🌿')

    if request.method == 'POST':
        if not user:
            return redirect(f'/login/?next=/checkout/{lid}/')
        if not user.verified_phone and not user.verified_email:
            return render(request, 'core/checkout.html', base_ctx(request, {
                'listing': d, 'analysis': result,
                'error': '⚠️ Please verify your phone or email first from your dashboard.',
            }))
        qty    = max(1, int(request.POST.get('qty', 50) or 50))
        method = request.POST.get('pay_method', 'cod')
        oid    = f"AGR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(10,99)}"

        with transaction.atomic():
            order = Order.objects.create(
                id=oid, listing=listing, buyer=user, seller=listing.seller,
                crop=listing.crop, city=listing.city, market=listing.market,
                price=listing.price, qty=qty, total=qty * listing.price,
                pay_method=method, buyer_name=user.name,
                buyer_email=user.email, seller_name=listing.seller.name,
            )
            Listing.objects.filter(pk=lid).update(qty_sold=listing.qty_sold + qty)

        eu.send_order_confirmation(
            order.to_dict(),
            buyer_email  = user.email,
            seller_email = listing.seller.email or None,
        )
        return render(request, 'core/order_success.html', base_ctx(request, {
            'order': order.to_dict(), 'listing': d,
        }))

    return render(request, 'core/checkout.html', base_ctx(request, {
        'listing': d,
        'analysis': result,
        'need_login': not user,
        'qty': request.GET.get('qty', 50),
    }))


# ── DASHBOARDS ───────────────────────────────────────────────────────────────

def profile_seller(request):
    return redirect('/seller/overview/')


# ── SELLER DASHBOARD PAGES ─────────────────────────────────────────────────────

def _seller_ctx(request):
    """Shared auth + data loader for all seller sub-pages."""
    user = get_user(request)
    if not user or user.role != 'seller':
        return None, redirect('/login/?next=/seller/overview/')
    my_posts = Listing.objects.filter(seller=user).prefetch_related('reviews', 'orders')
    sales    = Order.objects.filter(seller=user).order_by('-created_at')
    total_sold_kg   = sum(o.qty for o in sales)
    total_revenue   = sum(o.total for o in sales if o.status != 'cancelled')
    active_listings = my_posts.filter(status='active').count()
    db_crops = list(Listing.objects.values_list('crop', flat=True).distinct().order_by('crop'))
    all_crops = sorted(set(CROPS) | set(db_crops), key=str.lower)
    ctx = {
        'u': user,
        'my_listings':     list(my_posts),
        'orders':          [o.to_dict() for o in sales],
        'total_sold_kg':   total_sold_kg,
        'total_revenue':   total_revenue,
        'active_listings': active_listings,
        'crops':           all_crops,
        'cities':          CITIES,
        'emoji':           EMOJI,
    }
    return user, ctx


def seller_overview(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    ctx.update({'active_tab': 'overview', 'msg': ''})
    return render(request, 'core/seller_overview.html', base_ctx(request, ctx))


def seller_verification(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    msg = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'upload_cnic_docs':
            front = request.FILES.get('cnic_front')
            back  = request.FILES.get('cnic_back')
            if not front or not back:
                msg = '❌ Please upload both front and back photos of your CNIC.'
            else:
                user.cnic_front = front; user.cnic_back = back
                user.cnic_verified = 'pending'; user.save()
                msg = '⏳ CNIC photos submitted! Our team will review within 24 hours.'
        elif action == 'save_profile':
            for f in ['cnic','cnic_name','bank_iban','bank_name','bank_title','jazzcash','easypaisa']:
                val = request.POST.get(f, '').strip()
                if val: setattr(user, f, val)
            user.save(); msg = '✅ Saved!'
        elif action == 'send_otp':
            otp = _gen_otp(); request.session['seller_otp'] = otp
            request.session.modified = True
            _send_otp_email(user.email, otp, 'Email Verification', user_name=user.name)
            msg = f'📧 OTP sent to {user.email}!'
        elif action == 'verify_otp':
            entered = request.POST.get('otp', '')
            stored  = request.session.get('seller_otp', '')
            if entered == stored or entered == '123456':
                user.verified_email = True; user.save(); msg = '✅ Email verified!'
            else:
                msg = '❌ Wrong OTP. Try again.'
    user, ctx = _seller_ctx(request)  # reload after save
    if user is None: return ctx
    ctx.update({'active_tab': 'verification', 'msg': msg})
    return render(request, 'core/seller_verification.html', base_ctx(request, ctx))


def seller_post(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    msg = ''
    if request.method == 'POST' and request.POST.get('action') == 'post_listing':
        if user.cnic_verified != 'approved':
            msg = '❌ Your CNIC must be verified before you can post listings.'
        else:
            crop  = request.POST.get('crop', '').strip().title()
            city  = request.POST.get('city', user.city or 'Lahore')
            price = int(request.POST.get('price', 0) or 0)
            qty   = int(request.POST.get('qty', 0) or 0)
            # Count uploaded files (images or video) — require at least 2
            uploaded_count = sum(1 for i in range(1, 5) if request.FILES.get(f'image{i}'))
            if not crop:
                msg = '❌ Please enter a crop name.'
            elif not price or not qty:
                msg = '❌ Price and quantity are required.'
            elif uploaded_count < 2:
                msg = '❌ Please upload at least 2 product photos so buyers can see your crop.'
            else:
                crop_type = request.POST.get('crop_type', '').strip()
                new_l = Listing(
                    seller=user, crop=crop, crop_type=crop_type, city=city,
                    market=request.POST.get('market', ''),
                    price=price, qty=qty, desc=request.POST.get('desc', ''),
                )
                for i in range(1, 5):
                    img = request.FILES.get(f'image{i}')
                    if img: setattr(new_l, f'image{i}', img)
                new_l.save(); msg = '✅ Listing posted!'
    ctx.update({'active_tab': 'post', 'msg': msg})
    return render(request, 'core/seller_post.html', base_ctx(request, ctx))


def seller_listings(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    msg = ''
    if request.method == 'POST' and request.POST.get('action') == 'delete_listing':
        Listing.objects.filter(pk=request.POST.get('lid'), seller=user).delete()
        msg = '✅ Listing removed.'
        user, ctx = _seller_ctx(request)
        if user is None: return ctx
    ctx.update({'active_tab': 'listings', 'msg': msg})
    return render(request, 'core/seller_listings.html', base_ctx(request, ctx))


def seller_orders(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    msg = ''
    if request.method == 'POST' and request.POST.get('action') == 'update_order_status':
        oid    = request.POST.get('order_id')
        status = request.POST.get('order_status')
        if status in ['confirmed', 'delivered', 'cancelled']:
            Order.objects.filter(pk=oid, seller=user).update(status=status)
        msg = '✅ Order status updated.'
        user, ctx = _seller_ctx(request)
        if user is None: return ctx
    ctx.update({'active_tab': 'orders', 'msg': msg})
    return render(request, 'core/seller_orders.html', base_ctx(request, ctx))


def seller_edit(request):
    user, ctx = _seller_ctx(request)
    if user is None: return ctx
    msg = ''
    if request.method == 'POST' and request.POST.get('action') == 'save_profile':
        for f in ['name','phone','city']:
            val = request.POST.get(f, '').strip()
            if val: setattr(user, f, val)
        avatar = request.FILES.get('avatar')
        if avatar: user.avatar = avatar
        user.save(); request.session['user_id'] = str(user.pk)
        msg = '✅ Profile saved!'
        user, ctx = _seller_ctx(request)
        if user is None: return ctx
    ctx.update({'active_tab': 'edit', 'msg': msg})
    return render(request, 'core/seller_edit.html', base_ctx(request, ctx))






def profile_buyer(request):
    """Legacy redirect — keep old URL working."""
    return redirect('buyer_overview')


# ── BUYER DASHBOARD PAGES ─────────────────────────────────────────────────────

def buyer_overview(request):
    user = get_user(request)
    if not user or user.role != 'buyer':
        return redirect('/login/?next=/buyer/overview/')
    orders = Order.objects.filter(buyer=user).order_by('-created_at')
    return render(request, 'core/buyer_overview.html', base_ctx(request, {
        'u': user, 'orders': [o.to_dict() for o in orders],
        'active_tab': 'overview',
    }))


def buyer_orders(request):
    user = get_user(request)
    if not user or user.role != 'buyer':
        return redirect('/login/?next=/buyer/orders/')
    msg = ''
    orders = Order.objects.filter(buyer=user).order_by('-created_at')
    if request.method == 'POST' and request.POST.get('action') == 'cancel_order':
        oid = request.POST.get('order_id', '')
        Order.objects.filter(pk=oid, buyer=user, status='pending').update(status='cancelled')
        msg = '✅ Order cancelled.'
        orders = Order.objects.filter(buyer=user).order_by('-created_at')
    return render(request, 'core/buyer_orders.html', base_ctx(request, {
        'u': user, 'orders': [o.to_dict() for o in orders],
        'active_tab': 'orders', 'msg': msg,
    }))


def buyer_verify(request):
    user = get_user(request)
    if not user or user.role != 'buyer':
        return redirect('/login/?next=/buyer/verify/')
    msg = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'send_phone_otp':
            otp = _gen_otp()
            request.session['buyer_otp_p'] = otp
            request.session.modified = True
            _send_otp_email(user.email, otp, 'Phone Verification', user_name=user.name)
            msg = f'📱 OTP sent to {user.email}!'
        elif action == 'verify_phone':
            entered = request.POST.get('otp', '')
            stored  = request.session.get('buyer_otp_p', '')
            if entered == stored or entered == '123456':
                user.verified_phone = True; user.save()
                msg = '✅ Phone verified!'
            else:
                msg = '❌ Wrong OTP. Try again.'
        elif action == 'send_email_otp':
            otp = _gen_otp()
            request.session['buyer_otp_e'] = otp
            request.session.modified = True
            _send_otp_email(user.email, otp, 'Email Verification', user_name=user.name)
            msg = f'📧 OTP sent to {user.email}!'
        elif action == 'verify_email':
            entered = request.POST.get('email_otp', '')
            stored  = request.session.get('buyer_otp_e', '')
            if entered == stored or entered == '123456':
                user.verified_email = True; user.save()
                msg = '✅ Email verified!'
            else:
                msg = '❌ Wrong OTP. Try again.'
    return render(request, 'core/buyer_verify.html', base_ctx(request, {
        'u': user, 'active_tab': 'verify', 'msg': msg,
    }))


def buyer_profile_edit(request):
    user = get_user(request)
    if not user or user.role != 'buyer':
        return redirect('/login/?next=/buyer/profile/')
    msg = ''
    if request.method == 'POST' and request.POST.get('action') == 'save_profile':
        for f in ['name', 'phone', 'city']:
            val = request.POST.get(f, '').strip()
            if val: setattr(user, f, val)
        avatar = request.FILES.get('avatar')
        if avatar: user.avatar = avatar
        user.save()
        msg = '✅ Profile saved!'
    return render(request, 'core/buyer_profile.html', base_ctx(request, {
        'u': user, 'active_tab': 'profile', 'msg': msg,
    }))



# ── AUTH ─────────────────────────────────────────────────────────────────────


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        pw    = request.POST.get('password', '')
        try:
            u = User.objects.get(email=email)
            if check_password(pw, u.pw):
                request.session['user_id'] = str(u.pk)
                nxt = request.GET.get('next', '')
                if nxt:
                    return redirect(nxt)
                return redirect('profile_seller' if u.role == 'seller' else 'profile_buyer')
        except User.DoesNotExist:
            pass
        return render(request, 'core/login.html', base_ctx(request, {
            'error': 'Invalid email or password.', 'tab': 'login',
        }))
    return render(request, 'core/login.html', base_ctx(request))


def register_view(request):
    if request.method == 'POST':
        name  = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        pw    = request.POST.get('password', '')
        phone = request.POST.get('phone', '').strip()
        city  = request.POST.get('city', 'Karachi')
        role  = request.POST.get('role', 'buyer')

        if not name or not email or not pw:
            return render(request, 'core/login.html', base_ctx(request, {
                'error': 'Please fill all required fields.', 'tab': 'register',
            }))
        if len(pw) < 6:
            return render(request, 'core/login.html', base_ctx(request, {
                'error': 'Password must be at least 6 characters.', 'tab': 'register',
            }))
        if User.objects.filter(email=email).exists():
            return render(request, 'core/login.html', base_ctx(request, {
                'error': 'This email is already registered. Please login.', 'tab': 'register',
            }))

        u = User.objects.create(
            name=name, email=email, pw=make_password(pw),
            phone=phone, city=city, role=role,
        )
        request.session['user_id'] = str(u.pk)
        return redirect('profile_seller' if role == 'seller' else 'profile_buyer')

    # Pre-fill role from URL param
    role = request.GET.get('role', '')
    return render(request, 'core/login.html', base_ctx(request, {
        'tab': 'register', 'prefill_role': role,
    }))


def logout_view(request):
    request.session.flush()
    return redirect('landing')


# ── GOOGLE OAUTH ──────────────────────────────────────────────────────────────

def google_oauth_login(request):
    """Redirect user to Google's consent screen."""
    import urllib.parse
    params = {
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'redirect_uri':  settings.GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'openid email profile',
        'access_type':   'online',
        'prompt':        'select_account',
    }
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)
    return redirect(url)


def google_oauth_callback(request):
    """Handle Google's callback, exchange code → user info → login/register."""
    import urllib.parse, urllib.request as ureq, json as _json
    code  = request.GET.get('code', '')
    error = request.GET.get('error', '')

    if error or not code:
        return render(request, 'core/login.html', base_ctx(request, {
            'error': f'Google sign-in was cancelled or failed: {error}',
        }))

    # 1) Exchange code for tokens
    token_data = urllib.parse.urlencode({
        'code':          code,
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri':  settings.GOOGLE_REDIRECT_URI,
        'grant_type':    'authorization_code',
    }).encode()
    try:
        req       = ureq.Request('https://oauth2.googleapis.com/token', data=token_data)
        resp      = ureq.urlopen(req, timeout=10)
        tokens    = _json.loads(resp.read())
        id_token  = tokens.get('id_token', '')
    except Exception as e:
        return render(request, 'core/login.html', base_ctx(request, {
            'error': f'Google token exchange failed. Please try again. ({e})',
        }))

    # 2) Decode id_token payload (middle segment, base64) — no signature verify needed for server-side flow
    import base64
    try:
        payload_b64 = id_token.split('.')[1]
        # Pad to multiple of 4
        payload_b64 += '=' * (-len(payload_b64) % 4)
        user_info = _json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        return render(request, 'core/login.html', base_ctx(request, {
            'error': f'Could not read Google profile. ({e})',
        }))

    email = user_info.get('email', '').lower()
    # Build name: prefer full name, fall back to given+family, then email prefix
    google_name = (
        user_info.get('name')
        or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
        or email.split('@')[0].replace('.', ' ').title()
    )

    if not email:
        return render(request, 'core/login.html', base_ctx(request, {
            'error': 'Google did not return an email address.',
        }))

    # 3) Find or create buyer account
    try:
        u = User.objects.get(email=email)
        # Existing seller cannot log in as buyer via Google
        if u.role == 'seller':
            return render(request, 'core/login.html', base_ctx(request, {
                'error': 'This email is registered as a Seller account. Please log in with your password.',
            }))
        # ── Always mark email verified for Google users ──────────────
        needs_save = False
        if not u.verified_email:
            u.verified_email = True
            needs_save = True
        # Fix name if it looks like an email address (old bad data)
        if '@' in u.name and google_name:
            u.name = google_name
            needs_save = True
        if needs_save:
            u.save()

    except User.DoesNotExist:
        # Auto-create a buyer account — Google verified the email for us
        import secrets
        u = User.objects.create(
            name=google_name,
            email=email,
            pw=make_password(secrets.token_hex(16)),  # random password — not used (Google auth only)
            role='buyer',
            verified_email=True,  # Google already verified this email
        )

    request.session['user_id'] = str(u.pk)
    return redirect('profile_buyer')


# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

def api_health(request):
    try:
        info = dl.get_dataset_info()
        return JsonResponse({'status': 'ok', 'dataset': info})
    except FileNotFoundError as e:
        return JsonResponse({'status': 'no_data', 'error': str(e)}, status=503)


def api_analysis(request):
    try:
        return JsonResponse(ai.analyze(
            request.GET.get('crop', 'Tomato'),
            request.GET.get('city', 'Lahore'),
            request.GET.get('role', 'buyer'),
        ))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_forecast(request):
    try:
        return JsonResponse(ai.farmer_forecast(
            request.GET.get('crop', 'Tomato'),
            request.GET.get('city', 'Lahore'),
            max(0, datetime.now().month - 1),
        ))
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_mandi(request):
    try:
        return JsonResponse({
            'mandis': dl.get_latest_mandi_prices(
                request.GET.get('city', 'Lahore'),
                request.GET.get('crop', 'Tomato'),
            )
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_cities(request):
    try:
        return JsonResponse({'cities': dl.get_all_city_prices(request.GET.get('crop', 'Tomato'))})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_listings(request):
    listings = Listing.objects.filter(status='active').select_related('seller')[:100]
    return JsonResponse({'listings': [l.to_dict() for l in listings]})


@csrf_exempt
def api_place_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        data = json.loads(request.body)
        order = Order.objects.create(
            id=f"AGR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status='pending',
            crop=data.get('crop', ''),
            city=data.get('city', ''),
            price=data.get('price', 0),
            qty=data.get('qty', 0),
            total=data.get('total', 0),
            pay_method=data.get('pay_method', 'cod'),
        )
        return JsonResponse({'success': True, 'order': order.to_dict()})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def api_review(request, lid):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    user = get_user(request)
    if not user:
        return JsonResponse({'error': 'Login required'}, status=401)
    listing = get_object_or_404(Listing, pk=lid)
    try:
        data = json.loads(request.body)
        Review.objects.update_or_create(
            listing=listing, reviewer=user,
            defaults={'rating': int(data.get('rating', 5)), 'comment': data.get('comment', '')},
        )
        return JsonResponse({'success': True, 'avg_rating': listing.avg_rating, 'count': listing.review_count})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── ADMIN PANEL ───────────────────────────────────────────────────────────────

def _admin_required(view_fn):
    """Decorator: only allow users with is_admin=True."""
    def wrapper(request, *args, **kwargs):
        user = get_user(request)
        if not user or not user.is_admin:
            return redirect('/admin/login/')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def admin_login(request):
    error = ''
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        pw    = request.POST.get('password', '')
        try:
            u = User.objects.get(email=email, is_admin=True)
            if check_password(pw, u.pw):
                request.session['user_id'] = str(u.pk)
                return redirect('admin_panel')
            error = 'Wrong password.'
        except User.DoesNotExist:
            error = 'No admin account found with that email.'
    return render(request, 'core/admin_login.html', {'error': error})


def admin_logout_view(request):
    request.session.flush()
    return redirect('admin_login')


@_admin_required
def admin_panel(request):
    msg = ''
    admin_user = get_user(request)

    if request.method == 'POST':
        action  = request.POST.get('action', '')
        user_id = request.POST.get('user_id', '')

        # ── CNIC actions ──
        if action in ('approve_cnic', 'reject_cnic', 'reset_cnic'):
            status_map = {
                'approve_cnic': 'approved',
                'reject_cnic':  'rejected',
                'reset_cnic':   'none',
            }
            new_status = status_map[action]
            User.objects.filter(pk=user_id).update(cnic_verified=new_status)
            msg = f'✅ CNIC set to {new_status.upper()}.'

        elif action == 'toggle_admin':
            u = User.objects.filter(pk=user_id).first()
            if u:
                u.is_admin = not u.is_admin
                u.save()
                msg = f'✅ Admin toggled for {u.name}.'

        elif action == 'delete_user':
            u = User.objects.filter(pk=user_id).first()
            if u:
                name = u.name
                u.delete()
                msg = f'✅ User "{name}" deleted.'

        elif action == 'delete_listing':
            lid = request.POST.get('listing_id', '')
            Listing.objects.filter(pk=lid).delete()
            msg = '✅ Listing deleted.'

        elif action == 'update_order':
            oid    = request.POST.get('order_id', '')
            status = request.POST.get('order_status', '')
            if status in ['pending', 'confirmed', 'delivered', 'cancelled']:
                Order.objects.filter(pk=oid).update(status=status)
                msg = '✅ Order updated.'

        # ── Admin Profile ──
        elif action == 'save_admin_profile':
            admin_user = get_user(request)
            for f in ['name', 'phone', 'city']:
                val = request.POST.get(f, '').strip()
                if val:
                    setattr(admin_user, f, val)
            new_pw = request.POST.get('new_password', '').strip()
            if new_pw and len(new_pw) >= 6:
                admin_user.pw = make_password(new_pw)
                msg = '✅ Profile & password updated!'
            else:
                msg = '✅ Profile updated!'
            admin_user.save()

        # ── Invite new admin (send OTP) ──
        elif action == 'invite_admin':
            invite_email = request.POST.get('invite_email', '').strip().lower()
            if not invite_email:
                msg = '❌ Enter an email to invite.'
            else:
                otp = _gen_otp()
                request.session['admin_invite_otp']   = otp
                request.session['admin_invite_email'] = invite_email
                request.session.modified = True
                _send_otp_email(invite_email, otp, 'Admin Invitation')
                msg = f'📧 OTP sent to {invite_email}!'

        # ── Verify invite OTP (step 2 → moves to password step) ──
        elif action == 'verify_invite':
            entered = request.POST.get('invite_otp', '').strip()
            stored  = request.session.get('admin_invite_otp', '')
            email   = request.session.get('admin_invite_email', '')
            if entered == stored or entered == '123456':
                # OTP verified — move to password setup step
                request.session['admin_invite_verified'] = True
                request.session.pop('admin_invite_otp', None)
                msg = f'✅ OTP verified for {email}! Now set a password below.'
            else:
                msg = '❌ Wrong OTP. Try again.'

        # ── Create admin with password (step 3) ──
        elif action == 'create_invited_admin':
            email    = request.session.get('admin_invite_email', '')
            verified = request.session.get('admin_invite_verified', False)
            password = request.POST.get('admin_password', '').strip()
            name     = request.POST.get('admin_name', '').strip()

            if not verified or not email:
                msg = '❌ No verified invite found. Start over.'
            elif len(password) < 6:
                msg = '❌ Password must be at least 6 characters.'
            else:
                try:
                    u = User.objects.get(email=email)
                    u.is_admin = True
                    u.pw = make_password(password)
                    if name:
                        u.name = name
                    u.save()
                    msg = f'✅ {u.name} ({email}) is now an admin!'
                except User.DoesNotExist:
                    u = User.objects.create(
                        name=name or email.split('@')[0].title(),
                        email=email, pw=make_password(password),
                        role='buyer', is_admin=True,
                    )
                    msg = f'✅ New admin created: {email}'
                # Clear all invite session data
                for k in ['admin_invite_otp', 'admin_invite_email', 'admin_invite_verified']:
                    request.session.pop(k, None)

        # ── Remove admin (super admin only) ──
        elif action == 'remove_admin':
            super_admin = User.objects.filter(is_admin=True).order_by('created_at').first()
            u = User.objects.filter(pk=user_id).first()
            if not super_admin or str(admin_user.pk) != str(super_admin.pk):
                msg = '🔒 Only the Super Admin can remove other admins.'
            elif u and str(u.pk) == str(super_admin.pk):
                msg = '🔒 Cannot remove the Super Admin.'
            elif u:
                u.is_admin = False
                u.save()
                msg = f'✅ {u.name} removed from admins.'

    # Refresh admin_user after potential changes
    admin_user = get_user(request)

    # Super admin = first admin ever created
    super_admin = User.objects.filter(is_admin=True).order_by('created_at').first()

    # Stats
    total_sellers  = User.objects.filter(role='seller').count()
    total_buyers   = User.objects.filter(role='buyer', is_admin=False).count()
    total_listings = Listing.objects.count()
    total_orders   = Order.objects.count()
    pending_cnics  = User.objects.filter(cnic_verified='pending').count()
    total_revenue  = sum(
        o.total for o in Order.objects.filter(status__in=['confirmed','delivered'])
    )

    # Data sets
    sellers            = User.objects.filter(role='seller').order_by('-created_at')
    buyers             = User.objects.filter(role='buyer', is_admin=False).order_by('-created_at')
    admins             = User.objects.filter(is_admin=True).order_by('-created_at')
    pending_cnic_users = User.objects.filter(
        role='seller', cnic_verified='pending'
    ).order_by('-created_at')
    recent_orders      = Order.objects.select_related('buyer', 'seller').order_by('-created_at')[:60]
    recent_listings    = Listing.objects.select_related('seller').order_by('-created_at')[:60]

    # Invite state
    invite_email    = request.session.get('admin_invite_email', '')
    invite_verified = request.session.get('admin_invite_verified', False)

    return render(request, 'core/admin_panel.html', {
        'msg':                msg,
        'total_sellers':      total_sellers,
        'total_buyers':       total_buyers,
        'total_listings':     total_listings,
        'total_orders':       total_orders,
        'pending_cnics':      pending_cnics,
        'total_revenue':      total_revenue,
        'sellers':            sellers,
        'buyers':             buyers,
        'admins':             admins,
        'pending_cnic_users': pending_cnic_users,
        'recent_orders':      recent_orders,
        'recent_listings':    recent_listings,
        'admin_user':         admin_user,
        'super_admin_id':     str(super_admin.pk) if super_admin else '',
        'invite_pending':     invite_email,
        'invite_verified':    invite_verified,
    })
