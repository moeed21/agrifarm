"""
AgriBazaar — sendgrid_utils.py
Handles all transactional emails via SendGrid API.
Falls back to Django SMTP if SENDGRID_API_KEY is not configured.
"""
import random
import string
from django.conf import settings


# ── OTP GENERATOR ─────────────────────────────────────────────────────────────

def generate_otp(length=6):
    """Generate a secure random numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


# ── SENDGRID SENDER ───────────────────────────────────────────────────────────

def _send_via_sendgrid(to_email, subject, html_content, plain_text):
    """
    Send email via SendGrid API.
    Returns True on success, False on failure.
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent

        api_key    = getattr(settings, 'SENDGRID_API_KEY', '')
        from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', '')
        from_name  = getattr(settings, 'SENDGRID_FROM_NAME', 'AgriBazaar')

        if not api_key or api_key == 'your-sendgrid-api-key':
            return False  # Not configured — fall back to SMTP

        message = Mail(
            from_email   = Email(from_email, from_name),
            to_emails    = To(to_email),
            subject      = subject,
            html_content = html_content,
        )
        message.plain_text_content = plain_text

        sg   = SendGridAPIClient(api_key)
        resp = sg.send(message)
        success = 200 <= resp.status_code < 300
        if success:
            print(f'📧 [SendGrid] Email sent to {to_email} | {subject} (HTTP {resp.status_code})')
        else:
            print(f'⚠️  [SendGrid] Non-2xx response {resp.status_code} for {to_email}')
        return success
    except Exception as e:
        print(f'⚠️  [SendGrid] Error sending to {to_email}: {e}')
        return False


def _send_via_smtp(to_email, subject, plain_text, html_content):
    """Fallback: send email via Django's configured SMTP backend."""
    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(
            subject    = subject,
            body       = plain_text,
            from_email = settings.DEFAULT_FROM_EMAIL,
            to         = [to_email],
        )
        msg.attach_alternative(html_content, 'text/html')
        msg.send()
        print(f'📧 [SMTP]     Email sent to {to_email} | {subject}')
        return True
    except Exception as e:
        print(f'⚠️  [SMTP]     Error sending to {to_email}: {e}')
        return False


def send_email(to_email, subject, html_content, plain_text=''):
    """
    Primary email dispatcher.
    Tries SendGrid first; falls back to Django SMTP.
    Never raises — logs errors silently so the site never crashes.
    """
    if not plain_text:
        # Strip HTML tags for plain text fallback
        import re
        plain_text = re.sub(r'<[^>]+>', '', html_content)

    sent = _send_via_sendgrid(to_email, subject, html_content, plain_text)
    if not sent:
        _send_via_smtp(to_email, subject, plain_text, html_content)


# ── OTP EMAIL TEMPLATE ────────────────────────────────────────────────────────

def send_otp_email(to_email, otp, purpose='Verification', user_name=''):
    """
    Send a beautiful OTP email via SendGrid.

    Args:
        to_email  : recipient email address
        otp       : the 6-digit OTP code
        purpose   : e.g. 'Email Verification', 'Phone Verification', 'Admin Invitation'
        user_name : optional recipient name for personalisation
    """
    greeting = f'Hi {user_name},' if user_name else 'Hello,'

    subject = f'AgriBazaar — Your {purpose} Code: {otp}'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgriBazaar OTP</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: #f0f7f0;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
  }}
  .wrapper {{
    max-width: 520px;
    margin: 40px auto;
    background: #ffffff;
    border-radius: 20px;
    overflow: hidden;
    border: 2px solid #c8e6c9;
    box-shadow: 0 8px 32px rgba(27, 94, 32, 0.12);
  }}
  /* Header */
  .header {{
    background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 50%, #43a047 100%);
    padding: 36px 32px 28px;
    text-align: center;
  }}
  .logo-icon {{ font-size: 48px; margin-bottom: 10px; display: block; }}
  .header-title {{
    color: #ffffff;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.3px;
  }}
  .header-sub {{
    color: rgba(255,255,255,0.75);
    font-size: 13px;
    margin-top: 4px;
  }}
  /* Body */
  .body {{ padding: 36px 32px 28px; }}
  .greeting {{
    font-size: 15px;
    color: #2e7d32;
    font-weight: 600;
    margin-bottom: 10px;
  }}
  .intro-text {{
    font-size: 14px;
    color: #4a5568;
    line-height: 1.6;
    margin-bottom: 28px;
  }}
  /* OTP Box */
  .otp-box {{
    background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
    border: 2px dashed #66bb6a;
    border-radius: 16px;
    padding: 28px 24px;
    text-align: center;
    margin-bottom: 28px;
  }}
  .otp-label {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #388e3c;
    margin-bottom: 12px;
  }}
  .otp-code {{
    font-size: 48px;
    font-weight: 800;
    letter-spacing: 10px;
    color: #1b5e20;
    font-family: 'Courier New', monospace;
    display: block;
  }}
  .otp-expiry {{
    font-size: 12px;
    color: #81c784;
    margin-top: 12px;
    font-weight: 600;
  }}
  /* Warning */
  .warning-box {{
    background: #fffde7;
    border-left: 4px solid #f9a825;
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    color: #5d4037;
    margin-bottom: 24px;
    line-height: 1.5;
  }}
  .warning-box strong {{ color: #e65100; }}
  /* Info steps */
  .steps {{ margin-bottom: 24px; }}
  .step {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 10px;
    font-size: 13.5px;
    color: #37474f;
  }}
  .step-num {{
    background: #2e7d32;
    color: white;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }}
  /* Footer */
  .footer {{
    background: #f1f8e9;
    border-top: 1px solid #c8e6c9;
    padding: 20px 32px;
    text-align: center;
  }}
  .footer-text {{
    font-size: 12px;
    color: #78909c;
    line-height: 1.6;
  }}
  .footer-brand {{
    font-size: 13px;
    font-weight: 700;
    color: #2e7d32;
    margin-bottom: 4px;
  }}
</style>
</head>
<body>
<div class="wrapper">

  <!-- Header -->
  <div class="header">
    <span class="logo-icon">🌿</span>
    <div class="header-title">AgriBazaar</div>
    <div class="header-sub">Pakistan's AI Crop Intelligence Platform</div>
  </div>

  <!-- Body -->
  <div class="body">
    <p class="greeting">{greeting}</p>
    <p class="intro-text">
      You've requested a <strong>{purpose}</strong> code for your AgriBazaar account.
      Use the code below to complete the process.
    </p>

    <!-- OTP Display -->
    <div class="otp-box">
      <div class="otp-label">🔐 Your One-Time Password</div>
      <span class="otp-code">{otp}</span>
      <div class="otp-expiry">⏱ This code expires in <strong>10 minutes</strong></div>
    </div>

    <!-- Steps -->
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div>Copy the 6-digit code above</div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div>Return to the AgriBazaar verification page</div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div>Paste the code and click <strong>Verify</strong></div>
      </div>
    </div>

    <!-- Security Warning -->
    <div class="warning-box">
      🔒 <strong>Security Notice:</strong> AgriBazaar will <strong>never</strong> ask for your
      OTP by phone or chat. Do not share this code with anyone.
      If you did not request this, please ignore this email.
    </div>
  </div>

  <!-- Footer -->
  <div class="footer">
    <div class="footer-brand">🌿 AgriBazaar Pakistan</div>
    <div class="footer-text">
      This is an automated message — please do not reply.<br>
      &copy; 2025 AgriBazaar · Empowering Pakistan's Farmers
    </div>
  </div>

</div>
</body>
</html>"""

    plain = f"""AgriBazaar — {purpose} OTP

{greeting}

Your {purpose} code is: {otp}

This code expires in 10 minutes.

DO NOT share this code with anyone. AgriBazaar will never ask for your OTP.

If you did not request this, please ignore this email.

— AgriBazaar Pakistan
"""

    send_email(to_email, subject, html, plain)
    # Always log to console for dev convenience
    print(f'[OTP] {to_email} → {otp} ({purpose})')
