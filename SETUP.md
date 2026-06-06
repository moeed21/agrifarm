# AgriBazaar — Setup Guide (Updated)

## What's New in This Version
- ✅ **Real SQLite database** — users, listings, orders, reviews all persisted
- ✅ **Product image uploads** — sellers can add up to 4 photos per listing
- ✅ **Profile avatar uploads** — both buyers and sellers
- ✅ **Review system** — buyers who have placed & confirmed orders can review listings
- ✅ **Products sold counter** — qty_sold tracked per listing, shown on marketplace & profile
- ✅ **Order status management** — sellers can mark orders as confirmed/delivered/cancelled
- ✅ **Live weather (6+ months)** — Open-Meteo forecast + historical archive API (no hardcoding)
- ✅ **Listing detail page** — full image gallery, reviews, AI signal, buy button

---

## Quick Start

### 1. Install dependencies
```bash
pip install django pillow
```

### 2. Apply database migrations
```bash
cd agribazaar_django
python manage.py migrate
```

### 3. Seed demo data
```bash
python seed_demo.py
```

### 4. Add your CSV dataset
Place `clean_crop_prices.csv` in the project root (`agribazaar_django/`).

### 5. Run the server
```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000

---

## Demo Accounts
| Role   | Email             | Password |
|--------|-------------------|----------|
| Seller | seller@demo.com   | demo123  |
| Buyer  | buyer@demo.com    | demo123  |

---

## Database
- **Engine:** SQLite (file: `agribazaar.db` in project root)
- **Tables:** `ab_user`, `ab_listing`, `ab_order`, `ab_review`
- **Switch to PostgreSQL:** Change `DATABASES` in `agribazaar/settings.py`

## Media Files
- Uploaded images are stored in `media/` folder
- `MEDIA_ROOT = BASE_DIR / 'media'`
- Served at `/media/` in development

---

## Weather API
Uses **Open-Meteo** (free, no API key):
- `/v1/forecast` → 16-day live forecast (current month)
- `/archive-api.open-meteo.com/v1/archive` → historical monthly averages (months 1+)
- `/climate-api.open-meteo.com/v1/climate` → 30-year climate normals (fallback)
- Final fallback → Pakistan Met Dept hardcoded averages

## Email (optional)
Edit `agribazaar/settings.py`:
```python
EMAIL_HOST_USER     = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-gmail-app-password'
```
For dev, use the console backend (just uncomment the last line in settings.py).

---

## Production Checklist
- [ ] Change `SECRET_KEY`
- [ ] Set `DEBUG = False`
- [ ] Switch to PostgreSQL
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Configure proper email SMTP
- [ ] Use WhiteNoise or Nginx for static/media files
- [ ] Hash passwords (replace plain `pw` field with `make_password`)
