# AgriBazaar — Step-by-Step Deployment Guide

## What's Working ✅
- Landing page (no CSV needed)
- Marketplace (DB listings, no CSV needed)
- Login / Register / Logout
- OTP system (email + demo code shown on screen)
- Seller dashboard — post listings, manage orders, profile
- Buyer dashboard — orders, OTP verify, cancel orders
- Product images (upload to media/)
- Reviews + ratings
- AI Analysis (needs CSV)
- 6-month weather forecast (Open-Meteo + PMD fallback)
- Email notifications (Gmail SMTP)
- Crop type dropdown nav (Vegetables / Fruits / Grains / Cash Crops)

---

## OPTION A — Deploy on Railway (Recommended, Free)

### Step 1 — Install Git
Download from: https://git-scm.com/downloads → Install → restart terminal

### Step 2 — Create GitHub account
Go to github.com → Sign Up (free)

### Step 3 — Create a new GitHub repository
1. Click the "+" icon → "New repository"
2. Name it: `agribazaar`
3. Set to Public → Click "Create repository"

### Step 4 — Push your code
Open terminal/CMD in the `agribazaar_django` folder:
```bash
git init
git add .
git commit -m "AgriBazaar FYP - initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/agribazaar.git
git push -u origin main
```

### Step 5 — Deploy on Railway
1. Go to railway.app → Sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select `agribazaar` repo → Click Deploy
4. Wait 2-3 minutes → Railway gives you a live URL

### Step 6 — Set environment variables
In Railway → your project → "Variables" tab → Add these one by one:

| Variable | Value |
|---|---|
| `SECRET_KEY` | Go to djecrety.ir → copy the key |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app-name.railway.app` |
| `EMAIL_HOST_USER` | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Your Gmail app password (see below) |

### Step 7 — Run setup on Railway
In Railway → your service → "Deploy" tab → Open shell:
```bash
python manage.py migrate
python seed_demo.py
```

### Step 8 — Upload your CSV
In Railway shell:
```bash
# Upload via Railway's file browser or use their volume
# Place file at: /app/clean_crop_prices.csv
```

Your site is live! ✅

---

## OPTION B — Deploy on PythonAnywhere (Beginner-Friendly)

### Step 1 — Create account
Go to pythonanywhere.com → Sign up free

### Step 2 — Upload the zip file
1. Go to "Files" tab → Upload agribazaar_v6_final.zip
2. Open a Bash console (top right)

### Step 3 — Set up the project
```bash
unzip agribazaar_v6_final.zip
cd agribazaar_django
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py collectstatic --noinput
```

### Step 4 — Configure Web App
1. Go to "Web" tab → "Add a new web app"
2. Choose "Manual configuration" → Python 3.11
3. Fill in:
   - **Source code:** `/home/YOUR_USERNAME/agribazaar_django`
   - **Working directory:** `/home/YOUR_USERNAME/agribazaar_django`
   - **Virtualenv:** `/home/YOUR_USERNAME/agribazaar_django/venv`

### Step 5 — Edit WSGI file
Click "WSGI configuration file" link → Replace ALL content with:
```python
import sys, os
sys.path.insert(0, '/home/YOUR_USERNAME/agribazaar_django')
os.environ['DJANGO_SETTINGS_MODULE'] = 'agribazaar.settings'
os.environ['SECRET_KEY'] = 'paste-a-long-random-key-here'
os.environ['DEBUG'] = 'False'
os.environ['ALLOWED_HOSTS'] = 'YOUR_USERNAME.pythonanywhere.com'
os.environ['EMAIL_HOST_USER'] = 'your@gmail.com'
os.environ['EMAIL_HOST_PASSWORD'] = 'your-app-password'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Step 6 — Set static and media files
In Web tab → "Static files" section → Add:
| URL | Directory |
|---|---|
| `/static/` | `/home/YOUR_USERNAME/agribazaar_django/staticfiles` |
| `/media/` | `/home/YOUR_USERNAME/agribazaar_django/media` |

### Step 7 — Reload and visit
Click "Reload" → Visit `YOUR_USERNAME.pythonanywhere.com` ✅

---

## Setting Up Gmail OTP Emails

1. Go to myaccount.google.com
2. Security → 2-Step Verification → Enable
3. Search "App passwords" → Select app: Mail → Generate
4. Copy the 16-character password
5. Set `EMAIL_HOST_PASSWORD` to that password in your environment

---

## Demo Accounts
| Role | Email | Password |
|---|---|---|
| Seller | seller@demo.com | demo123 |
| Buyer | buyer@demo.com | demo123 |

OTP bypass: enter `123456` for any OTP field in demo mode.

---

## Uploading Your CSV

The CSV must be named `clean_crop_prices.csv` and placed in the project root.

**Required columns:** `date`, `crop`, `city`, `market_name`, `avg_price`, `min_price`, `max_price`, `month`

Without the CSV:
- Landing page ✅ works
- Marketplace ✅ works  
- Login/Register ✅ works
- AI Analysis ❌ shows "no data" page
- Weather still works (PMD fallback)

---

## Common Errors

| Error | Fix |
|---|---|
| `DisallowedHost` | Add your domain to `ALLOWED_HOSTS` |
| `500 on login` | Check `SECRET_KEY` is set |
| Images not showing | Run `python manage.py collectstatic` |
| OTP not sending | Check Gmail app password is correct |
| `no module whitenoise` | Run `pip install -r requirements.txt` |
| AI Analysis blank | Add `clean_crop_prices.csv` to project root |
