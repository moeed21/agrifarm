from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('',                        views.landing,          name='landing'),
    path('analysis/',               views.analysis,         name='analysis'),
    path('marketplace/',            views.marketplace,      name='marketplace'),
    path('listing/<int:lid>/',      views.listing_detail,   name='listing_detail'),
    path('checkout/<int:lid>/',     views.checkout,         name='checkout'),
    path('login/',                  views.login_view,           name='login'),
    path('register/',               views.register_view,        name='register'),
    path('logout/',                 views.logout_view,          name='logout'),
    path('auth/google/',            views.google_oauth_login,   name='google_login'),
    path('auth/google/callback/',   views.google_oauth_callback,name='google_callback'),
    path('profile/seller/',         views.profile_seller,       name='profile_seller'),
    path('seller/overview/',        views.seller_overview,      name='seller_overview'),
    path('seller/verification/',    views.seller_verification,  name='seller_verification'),
    path('seller/post/',            views.seller_post,          name='seller_post'),
    path('seller/listings/',        views.seller_listings,      name='seller_listings'),
    path('seller/orders/',          views.seller_orders,        name='seller_orders'),
    path('seller/edit/',            views.seller_edit,          name='seller_edit'),
    path('buyer/overview/',      views.buyer_overview,      name='buyer_overview'),
    path('buyer/orders/',        views.buyer_orders,        name='buyer_orders'),
    path('buyer/verify/',        views.buyer_verify,        name='buyer_verify'),
    path('buyer/profile/',       views.buyer_profile_edit,  name='buyer_profile'),
    path('profile/buyer/',       views.profile_buyer,       name='profile_buyer'),
    # API
    path('api/health/',             views.api_health,       name='api_health'),
    path('api/analysis/',           views.api_analysis,     name='api_analysis'),
    path('api/forecast/',           views.api_forecast,     name='api_forecast'),
    path('api/mandi/',              views.api_mandi,        name='api_mandi'),
    path('api/cities/',             views.api_cities,       name='api_cities'),
    path('api/listings/',           views.api_listings,     name='api_listings'),
    path('api/place-order/',        views.api_place_order,  name='api_place_order'),
    path('api/review/<int:lid>/',   views.api_review,       name='api_review'),
    # Admin Panel
    path('admin/',                  views.admin_panel,      name='admin_panel'),
    path('admin/login/',            views.admin_login,      name='admin_login'),
    path('admin/logout/',           views.admin_logout_view,name='admin_logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
