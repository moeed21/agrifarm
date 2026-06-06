"""
AgriBazaar — email_utils.py
Sends order confirmation emails to buyer and seller.
Works with Gmail SMTP or console backend (for development).
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings

EMOJI = {'Tomato':'🍅','Potato':'🥔','Onion':'🧅','Garlic':'🧄',
         'Carrot':'🥕','Peas':'🫛','Cucumber':'🥒','Brinjal':'🍆'}

PAY_LABELS = {
    'cod':       'Cash on Delivery',
    'jazzcash':  'JazzCash',
    'easypaisa': 'EasyPaisa',
    'bank':      'Bank Transfer (IBFT)',
}


def send_order_confirmation(order, buyer_email=None, seller_email=None):
    """
    Send order confirmation email to buyer (and optionally seller).
    Gracefully handles missing email config — logs error, doesn't crash.
    """
    emoji = EMOJI.get(order.get('crop',''), '🌿')
    pay   = PAY_LABELS.get(order.get('pay_method','cod'), order.get('pay_method',''))

    # ── BUYER EMAIL ───────────────────────────────────────────
    if buyer_email:
        buyer_subject = f"✅ Order Confirmed — {order['crop']} | AgriBazaar"
        buyer_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body{{margin:0;padding:0;background:#f5faf6;font-family:'Segoe UI',Arial,sans-serif}}
  .wrap{{max-width:560px;margin:30px auto;background:#fff;border-radius:16px;overflow:hidden;border:2px solid #d1e8d8;box-shadow:0 4px 16px rgba(10,46,26,.12)}}
  .hd{{background:linear-gradient(135deg,#1a5c35,#2d9148);padding:28px;text-align:center}}
  .hd-logo{{font-size:36px;margin-bottom:8px}}
  .hd-title{{color:#fff;font-size:22px;font-weight:800;margin-bottom:4px}}
  .hd-sub{{color:rgba(255,255,255,.7);font-size:13px}}
  .body{{padding:24px}}
  .success-box{{background:#f0fdf4;border:2px solid #a8e6bb;border-radius:12px;padding:16px;text-align:center;margin-bottom:20px}}
  .success-icon{{font-size:40px;margin-bottom:8px}}
  .success-id{{font-size:12px;color:#6b7c70;font-family:monospace;margin-top:4px}}
  .detail-table{{width:100%;border-collapse:collapse;margin-bottom:20px}}
  .detail-table tr td{{padding:9px 12px;font-size:13.5px;border-bottom:1px solid #d4f5df}}
  .detail-table tr:last-child td{{border:none}}
  .detail-table .lbl{{color:#6b7c70;font-weight:600;width:40%}}
  .detail-table .val{{font-weight:800;color:#0f1a12}}
  .total-row{{background:#f0fdf4}}
  .total-row .val{{color:#1a5c35;font-size:16px}}
  .info-box{{background:#fffbeb;border:1.5px solid #fde68a;border-radius:10px;padding:14px;font-size:13px;color:#92400e;margin-bottom:18px}}
  .btn{{display:inline-block;background:linear-gradient(135deg,#1a5c35,#2d9148);color:#fff;padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:800;font-size:14px;margin:8px 4px}}
  .footer{{background:#f5faf6;padding:18px;text-align:center;font-size:11.5px;color:#6b7c70;border-top:1px solid #d1e8d8}}
</style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <div class="hd-logo">🌿</div>
    <div class="hd-title">Order Confirmed!</div>
    <div class="hd-sub">AgriBazaar — Pakistan's Crop Intelligence Platform</div>
  </div>
  <div class="body">
    <div class="success-box">
      <div class="success-icon">{emoji}</div>
      <div style="font-weight:800;font-size:18px;color:#1a5c35">Your order is placed!</div>
      <div style="font-size:13px;color:#6b7c70;margin-top:5px">Hi <strong>{order.get('buyer','')}</strong>, your order has been received.</div>
      <div class="success-id">{order['id']}</div>
    </div>

    <table class="detail-table">
      <tr><td class="lbl">Crop</td><td class="val">{emoji} {order['crop']}</td></tr>
      <tr><td class="lbl">City</td><td class="val">📍 {order['city']}</td></tr>
      <tr><td class="lbl">Market</td><td class="val">🏪 {order.get('market','')}</td></tr>
      <tr><td class="lbl">Quantity</td><td class="val">📦 {order['qty']} kg</td></tr>
      <tr><td class="lbl">Price</td><td class="val">{order['price']} PKR/kg</td></tr>
      <tr><td class="lbl">Payment</td><td class="val">💳 {pay}</td></tr>
      <tr><td class="lbl">Status</td><td class="val">⏳ Pending</td></tr>
      <tr class="total-row"><td class="lbl" style="font-weight:800;color:#1a5c35">Total Amount</td><td class="val">{order['total']:,} PKR</td></tr>
    </table>

    <div class="info-box">
      {'📞 <strong>Cash on Delivery:</strong> The seller will contact you to arrange delivery. Please keep your phone handy.' if order.get('pay_method') == 'cod' else f'💳 <strong>{pay}:</strong> Please transfer <strong>{order["total"]:,} PKR</strong> to the seller\'s account. Share your transaction ID on WhatsApp.'}
    </div>

    <div style="text-align:center">
      <a href="http://127.0.0.1:8000/profile/buyer/" class="btn">📋 View My Orders</a>
      <a href="http://127.0.0.1:8000/marketplace/" class="btn" style="background:linear-gradient(135deg,#b45309,#d97706)">🛒 Shop More</a>
    </div>
  </div>
  <div class="footer">
    © 2025 AgriBazaar · Pakistan's AI Crop Intelligence Platform<br>
    Order ID: {order['id']} · Date: {order.get('date','')}
  </div>
</div>
</body>
</html>
"""
        buyer_text = f"""
AgriBazaar — Order Confirmed!

Hi {order.get('buyer','')},

Your order has been placed successfully.

Order ID : {order['id']}
Crop     : {order['crop']}
City     : {order['city']}
Market   : {order.get('market','')}
Quantity : {order['qty']} kg
Price    : {order['price']} PKR/kg
Payment  : {pay}
Total    : {order['total']:,} PKR
Status   : Pending

{'The seller will contact you to arrange delivery (COD).' if order.get('pay_method') == 'cod' else f'Please transfer {order["total"]:,} PKR to the seller account.'}

Track your order: http://127.0.0.1:8000/profile/buyer/

AgriBazaar Team
"""
        _send(buyer_email, buyer_subject, buyer_text, buyer_html)

    # ── SELLER EMAIL ──────────────────────────────────────────
    if seller_email:
        seller_subject = f"📬 New Order Received — {order['crop']} {order['qty']}kg | AgriBazaar"
        seller_text = f"""
AgriBazaar — New Order Received!

You have a new order on AgriBazaar.

Order ID : {order['id']}
Crop     : {order['crop']}
City     : {order['city']}
Quantity : {order['qty']} kg
Price    : {order['price']} PKR/kg
Total    : {order['total']:,} PKR
Payment  : {pay}
Buyer    : {order.get('buyer','')}
Date     : {order.get('date','')}

Please contact the buyer to confirm delivery.
View your orders: http://127.0.0.1:8000/profile/seller/

AgriBazaar Team
"""
        seller_html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
  body{{margin:0;padding:0;background:#f5faf6;font-family:'Segoe UI',Arial,sans-serif}}
  .wrap{{max-width:520px;margin:30px auto;background:#fff;border-radius:16px;overflow:hidden;border:2px solid #d1e8d8}}
  .hd{{background:linear-gradient(135deg,#0f3d22,#1a5c35);padding:22px;text-align:center}}
  .hd-title{{color:#fff;font-size:19px;font-weight:800;margin-top:6px}}
  .body{{padding:22px}}
  .order-box{{background:#f0fdf4;border:2px solid #a8e6bb;border-radius:12px;padding:16px;margin-bottom:18px}}
  .row{{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #d4f5df;font-size:13.5px}}
  .row:last-child{{border:none}}
  .lbl{{color:#6b7c70;font-weight:600}}.val{{font-weight:800;color:#0f1a12}}
  .btn{{display:inline-block;background:linear-gradient(135deg,#1a5c35,#2d9148);color:#fff;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:800;font-size:14px}}
  .footer{{background:#f5faf6;padding:16px;text-align:center;font-size:11.5px;color:#6b7c70;border-top:1px solid #d1e8d8}}
</style></head>
<body><div class="wrap">
  <div class="hd"><div style="font-size:32px">📬</div><div class="hd-title">New Order Received!</div></div>
  <div class="body">
    <div class="order-box">
      <div class="row"><span class="lbl">Order ID</span><span class="val" style="font-family:monospace;font-size:11px">{order['id']}</span></div>
      <div class="row"><span class="lbl">Crop</span><span class="val">{emoji} {order['crop']}</span></div>
      <div class="row"><span class="lbl">Quantity</span><span class="val">📦 {order['qty']} kg</span></div>
      <div class="row"><span class="lbl">Price</span><span class="val">{order['price']} PKR/kg</span></div>
      <div class="row"><span class="lbl">Payment</span><span class="val">💳 {pay}</span></div>
      <div class="row"><span class="lbl">Buyer</span><span class="val">👤 {order.get('buyer','')}</span></div>
      <div class="row" style="background:#e6f7ef;border-radius:8px;padding:10px;border:none"><span class="lbl" style="color:#1a5c35;font-weight:800">TOTAL</span><span class="val" style="color:#1a5c35;font-size:17px">{order['total']:,} PKR</span></div>
    </div>
    <p style="font-size:13.5px;color:#2d3e32;margin-bottom:18px">Please contact the buyer to confirm and arrange delivery.</p>
    <div style="text-align:center"><a href="http://127.0.0.1:8000/profile/seller/" class="btn">📋 Manage Orders</a></div>
  </div>
  <div class="footer">© 2025 AgriBazaar · {order.get('date','')}</div>
</div></body></html>
"""
        _send(seller_email, seller_subject, seller_text, seller_html)


def _send(to_email, subject, text_body, html_body):
    """
    Send email via SendGrid (primary) with SMTP fallback.
    Never raises — site never crashes from an email failure.
    """
    try:
        from .sendgrid_utils import send_email
        send_email(to_email, subject, html_body, plain_text=text_body)
    except Exception as e:
        print(f"⚠️  Email not sent to {to_email}: {e}")
