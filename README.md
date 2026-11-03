# Ghorify: Smart House Rental & Property Matching System

A Django web app for renting homes in Dhaka. One account can do both: look for a home (see homes
ranked by a **match percentage**, check the **real monthly cost**, save favourites and compare 2-3
of them side by side) and post its own properties with photos and bills. Admins verify users and
moderate listings.

CSE 302 project, University of Asia Pacific.

## Apps and models

| App | Models | Purpose |
|---|---|---|
| `accounts` | `User`, `Profile` | One account per person (user or admin), phone login, avatar, NID / Birth Certificate verification |
| `properties` | `Property`, `PropertyImage`, `Utility`, `Amenity` | Listings, photo gallery (media CRUD), utility bills for the monthly cost estimate |
| `search` | (no models) | Smart match page and the matching engine (`search/matching.py`) |
| `interactions` | `Favourite`, `Comparison`, `ComparisonItem` | Favourite homes and side-by-side comparison of 2-3 favourites |
| `dashboard` | (no models) | User dashboard and the admin panel (listing moderation, verification, users) |

## Listing details

- Dhaka city only: every listing belongs to an area of Dhaka (Dhanmondi, Mirpur, Uttara, ...)
- Categories: Family, Bachelor, Sublet
- "Who can rent" (Anyone / Male only / Female only) is asked only for bachelor listings
- Balconies, floor, negotiable or fixed rent, optional service charge, parking, pets, amenities and house rules
- Every post needs at least one photo
- Logged-in users can see the landowner's phone number (with a copy button) from the Contact button

## Business rules

- One account can save and compare homes **and** post properties. Admin accounts only moderate.
- New listings start as **pending** until an admin approves them. Uploading an NID or Birth
  Certificate is optional; once an admin verifies it, the owner's posts show a ✓ Verified badge.
- Editing a rejected listing sends it back for review.
- Guests must log in to see a landowner's phone number (with a copy button) and the exact address.
- Compare works on favourites: pick 2 or 3 favourite homes. With no favourites, the page asks you to
  favourite some first.
- Users log in with their phone number (or email); there is no separate username.
- Smart Match (button on the listing page): every home inside the min and max budget that matches
  fully or partly is shown, highest match % first.

### Match percentage

Each preference the user fills in has a weight: budget 30, area 20, bedrooms 15, bathrooms 10,
category 10, amenities 10, gender 8, type 6, parking 5, pets 5. A property earns full,
partial (e.g. one bedroom less gives half) or zero points per preference, and
`match % = earned / possible × 100`. Smart Match shows every home inside the budget with a match above 0%, highest match first.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo     # demo users, listings and photos
python manage.py runserver
```

Open http://127.0.0.1:8000. Step-by-step instructions (in Banglish) are in `HOW_TO_RUN.txt`.
To rebuild the demo data from scratch, run `python manage.py seed_demo --reset`.

Demo accounts (password `ghorify123`): `admin` (platform admin); Rahim `01711000001` and
Nasrin `01811000002` (verified, have listings); Kamal `01911000003` (waiting for verification);
Tanvir `01611000004`, Mim `01511000005` and Sakib `01311000006` (looking for a home).

Run the tests with `python manage.py test`.

Demo listing photos (`static/img/photos/bd_*.jpg`) are real photos from Bangladesh taken from Wikimedia Commons; each photo's author and licence is listed in `static/img/photos/CREDITS.md`. The home page background is a drone photo of Hatirjheel, Dhaka (credit in the same file).

## Requirements

```
Django==6.1.2
pillow==13.0.0
asgiref==3.13.0
sqlparse==0.6.0
tzdata==2026.6
```
