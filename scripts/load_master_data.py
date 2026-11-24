import random
from odoo_client import Odoo

random.seed(42)
o = Odoo()
uae = o.find("res.country", [("code", "=", "AE")])

CUSTOMERS = [
    ("Al Noor Fresh Supermarket LLC", "Dubai", "Al Quoz Industrial Area 3"),
    ("Gulf Basket Trading LLC", "Dubai", "Deira, Al Rigga Road"),
    ("Marina Mart Grocery", "Dubai", "Dubai Marina Walk"),
    ("Desert Palm Hypermarket", "Abu Dhabi", "Mussafah Industrial Area"),
    ("Corniche Daily Needs LLC", "Abu Dhabi", "Al Khalidiyah"),
    ("Sahara Cash & Carry", "Sharjah", "Industrial Area 12"),
    ("Falcon Catering Services", "Dubai", "Al Barsha South"),
    ("Pearl Hotel Supplies LLC", "Dubai", "Jumeirah Lakes Towers"),
    ("Oasis Canteen Solutions", "Al Ain", "Al Sanaiya"),
    ("Emirates Family Mart", "Ajman", "Al Jurf Industrial"),
    ("Blue Dune Restaurants Group", "Dubai", "Business Bay"),
    ("Al Wasl Minimarket", "Dubai", "Satwa"),
    ("Khalifa Staff Catering LLC", "Abu Dhabi", "ICAD Musaffah"),
    ("Mirage Cafe Chain", "Sharjah", "Al Majaz"),
    ("Coral Bay Resort Supplies", "Ras Al Khaimah", "Al Hamra"),
    ("Nakheel Fresh Foods Trading", "Dubai", "Ras Al Khor"),
    ("Horizon School Canteens", "Abu Dhabi", "Al Reem Island"),
    ("Silver Sands Cafeteria", "Fujairah", "Fujairah Free Zone Area"),
    ("Qasr Al Bahr Grocery", "Al Ain", "Al Jimi"),
    ("Metro Value Stores LLC", "Sharjah", "Muwaileh"),
]

SUPPLIERS = [
    ("Gulf Grains Import Export FZE", "Dubai", "Jebel Ali Free Zone"),
    ("Al Safa Beverages Industries", "Sharjah", "Sajaa Industrial Area"),
    ("Pure Home Care Manufacturing", "Abu Dhabi", "KIZAD Khalifa Industrial Zone"),
    ("Eastern Spice & Oil Trading", "Dubai", "Ras Al Khor Industrial"),
    ("Paper Plus Packaging LLC", "Ajman", "Al Jurf Industrial"),
    ("Fresh Dairy Distribution Co", "Al Ain", "Al Ain Industrial Area"),
    ("Orient Personal Care FZCO", "Dubai", "Dubai Silicon Oasis"),
    ("National Sugar & Tea Traders", "Dubai", "Deira Naif"),
]

# (code, name, category, cost AED, sale price AED)
PRODUCTS = [
    ("FS001", "Basmati Rice 5kg", "Food Staples", 22, 28),
    ("FS002", "Sunflower Oil 1.5L", "Food Staples", 9, 12),
    ("FS003", "White Sugar 2kg", "Food Staples", 6, 8),
    ("FS004", "Wheat Flour 5kg", "Food Staples", 11, 15),
    ("FS005", "Red Lentils 1kg", "Food Staples", 5, 7),
    ("FS006", "Chickpeas 1kg", "Food Staples", 6, 8.5),
    ("FS007", "Tomato Paste 800g", "Food Staples", 7, 9.5),
    ("FS008", "Dates 1kg", "Food Staples", 14, 19),
    ("FS009", "Black Tea 100 Bags", "Food Staples", 8, 11),
    ("FS010", "Instant Coffee 200g", "Food Staples", 16, 22),
    ("FS011", "Spaghetti 500g", "Food Staples", 3, 4.5),
    ("BV001", "Bottled Water 500ml x24", "Beverages", 8, 11),
    ("BV002", "Bottled Water 1.5L x12", "Beverages", 9, 12.5),
    ("BV003", "Orange Juice 1L x12", "Beverages", 28, 36),
    ("BV004", "Cola Drink 330ml x24", "Beverages", 30, 38),
    ("BV005", "Energy Drink 250ml x24", "Beverages", 45, 58),
    ("BV006", "Laban 1L x12", "Beverages", 24, 31),
    ("CH001", "Dishwashing Liquid 750ml", "Cleaning and Household", 4, 6),
    ("CH002", "Laundry Powder 3kg", "Cleaning and Household", 22, 29),
    ("CH003", "Floor Cleaner 1.5L", "Cleaning and Household", 6, 8.5),
    ("CH004", "Bleach 1L", "Cleaning and Household", 3.5, 5),
    ("CH005", "Toilet Tissue 48 Rolls", "Cleaning and Household", 24, 32),
    ("CH006", "Kitchen Roll 6 Pack", "Cleaning and Household", 9, 12),
    ("CH007", "Garbage Bags 30 Pack", "Cleaning and Household", 5, 7.5),
    ("PC001", "Hand Soap 500ml", "Personal Care", 4, 6),
    ("PC002", "Shampoo 400ml", "Personal Care", 9, 13),
    ("PC003", "Toothpaste 120g", "Personal Care", 4.5, 6.5),
    ("PC004", "Hand Sanitizer 500ml", "Personal Care", 7, 10),
    ("PK001", "Food Containers 500ml x50", "Packaging and Disposables", 12, 17),
    ("PK002", "Paper Cups 8oz x50", "Packaging and Disposables", 6, 9),
    ("PK003", "Aluminium Foil 30cm", "Packaging and Disposables", 8, 11.5),
    ("PK004", "Cling Film 300m", "Packaging and Disposables", 9, 13),
]


def make_partner(name, city, street):
    if o.find("res.partner", [("name", "=", name)]):
        return False
    vals = {
        "name": name,
        "is_company": True,
        "company_type": "company",
        "street": street,
        "city": city,
        "country_id": uae,
    }
    trn = "100" + "".join(random.choice("0123456789") for _ in range(12))
    try:
        o.call("res.partner", "create", dict(vals, vat=trn))
    except Exception:
        o.call("res.partner", "create", vals)
    return True


def get_category(name):
    cid = o.find("product.category", [("name", "=", name)])
    return cid or o.call("product.category", "create", {"name": name})


print("Creating customers...")
n = sum(make_partner(*c) for c in CUSTOMERS)
print(f"  created {n} new customers")

print("Creating suppliers...")
n = sum(make_partner(*s) for s in SUPPLIERS)
print(f"  created {n} new suppliers")

print("Creating products...")
created = 0
for code, name, cat, cost, price in PRODUCTS:
    if o.find("product.template", [("default_code", "=", code)]):
        continue
    o.call("product.template", "create", {
        "name": name,
        "default_code": code,
        "type": "consu",
        "is_storable": True,
        "list_price": price,
        "standard_price": cost,
        "categ_id": get_category(cat),
        "sale_ok": True,
        "purchase_ok": True,
    })
    created += 1
print(f"  created {created} new products")

print("Done. Totals in Odoo now:")
print("  companies/partners:", o.call("res.partner", "search_count", [("is_company", "=", True)]))
print("  products:", o.call("product.template", "search_count", [("default_code", "!=", False)]))
