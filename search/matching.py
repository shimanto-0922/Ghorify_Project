# Ghorify match engine
#
# The user says what they want on the Smart Match page.
# Every property gets points only for the preferences the user filled in,
# so an empty field never lowers the score.
#
#     match % = points earned / points possible * 100
#
# Only homes inside the min and max budget are shown. Some preferences give
# half points, e.g. a flat with one bedroom less than asked.

from decimal import Decimal


WEIGHTS = {
    'budget': 30,
    'location': 20,
    'bedrooms': 15,
    'bathrooms': 10,
    'category': 10,
    'amenities': 10,
    'property_type': 6,
    'gender': 8,
    'parking': 5,
    'pet_friendly': 5,
}

def budget_score(prop, prefs):
    max_price = prefs.get('max_price')
    min_price = prefs.get('min_price')
    if not max_price and not min_price:
        return None

    if prefs.get('budget_includes_bills'):
        cost = prop.monthly_cost
    else:
        cost = Decimal(prop.price)

    if min_price and cost < min_price:
        return 0.5      # cheaper than expected, still worth showing
    if not max_price or cost <= max_price:
        return 1.0
    over = float(cost) / float(max_price)
    if over <= 1.10:
        return 0.5
    if over <= 1.20:
        return 0.25
    return 0.0


def location_score(prop, prefs):
    wanted = (prefs.get('location') or '').strip().lower()
    if not wanted:
        return None
    area = prop.location.lower()
    if wanted == area or wanted in area or area in wanted:
        return 1.0
    if wanted in prop.address.lower():
        return 0.5
    return 0.0


def at_least_score(actual, wanted):
    if not wanted:
        return None
    if actual >= wanted:
        return 1.0
    if actual == wanted - 1:
        return 0.5
    return 0.0


def exact_score(actual, wanted):
    if not wanted:
        return None
    if actual == wanted:
        return 1.0
    return 0.0


def required_score(actual, required):
    if not required:
        return None
    if actual:
        return 1.0
    return 0.0


def gender_score(prop, prefs):
    gender = prefs.get('tenant_gender')
    if not gender:
        return None
    if prop.tenant_gender == 'any' or prop.tenant_gender == gender:
        return 1.0
    return 0.0


def amenities_score(prop, prefs):
    wanted = set()
    for amenity in prefs.get('amenities') or []:
        wanted.add(amenity.id)
    if not wanted:
        return None
    have = set()
    for amenity in prop.amenities.all():
        have.add(amenity.id)
    return len(wanted & have) / len(wanted)


def match_level(percentage):
    if percentage >= 85:
        return 'excellent'
    if percentage >= 65:
        return 'good'
    return 'fair'


def score_property(prop, prefs):
    # Each part is (key, label shown on the page, score from 0 to 1 or None)
    parts = [
        ('budget', 'Within budget', budget_score(prop, prefs)),
        ('location', 'Preferred area', location_score(prop, prefs)),
        ('bedrooms', 'Bedrooms', at_least_score(prop.bedrooms, prefs.get('min_bedrooms'))),
        ('bathrooms', 'Bathrooms', at_least_score(prop.bathrooms, prefs.get('min_bathrooms'))),
        ('category', 'Category', exact_score(prop.category, prefs.get('category'))),
        ('property_type', 'Property type', exact_score(prop.property_type, prefs.get('property_type'))),
        ('amenities', 'Amenities', amenities_score(prop, prefs)),
        ('gender', 'Allowed for you', gender_score(prop, prefs)),
        ('parking', 'Parking', required_score(prop.parking, prefs.get('needs_parking'))),
        ('pet_friendly', 'Pet friendly', required_score(prop.pet_friendly, prefs.get('needs_pet_friendly'))),
    ]

    earned = 0.0
    possible = 0.0
    reasons = []
    for key, label, value in parts:
        if value is None:
            continue
        earned += WEIGHTS[key] * value
        possible += WEIGHTS[key]
        reasons.append((label, value))

    if possible:
        percentage = round(earned / possible * 100)
    else:
        percentage = 100

    return {
        'property': prop,
        'percentage': percentage,
        'reasons': reasons,
        'level': match_level(percentage),
    }


def within_budget(prop, prefs):
    # Rent (or rent + bills) must be between the min and max budget
    if prefs.get('budget_includes_bills'):
        cost = prop.monthly_cost
    else:
        cost = Decimal(prop.price)
    if prefs.get('min_price') and cost < prefs['min_price']:
        return False
    if prefs.get('max_price') and cost > prefs['max_price']:
        return False
    return True


def smart_match(properties, prefs):
    # Every home inside the budget that matches fully or partly is shown,
    # the highest match % first.
    if prefs.get('tenant_gender'):
        # A male only flat is never right for a female tenant (and the other way)
        properties = properties.filter(tenant_gender__in=['any', prefs['tenant_gender']])

    results = []
    for prop in properties:
        if not within_budget(prop, prefs):
            continue
        result = score_property(prop, prefs)
        if result['percentage'] > 0:
            results.append(result)
    results.sort(key=lambda r: (r['percentage'], r['property'].created_at), reverse=True)
    return results
