import xmlrpc.client
import getpass

URL = "http://localhost:8069"
DB = "nexusai"

email = input("Odoo admin email: ")
password = getpass.getpass("Odoo admin password: ")

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
print("Odoo version:", common.version()["server_version"])

uid = common.authenticate(DB, email, password, {})
if not uid:
    print("LOGIN FAILED: check the database name, email and password")
    raise SystemExit(1)
print("Login OK, user id:", uid)

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, password, model, method, list(args), kwargs)

company = call("res.company", "search_read", [], fields=["name", "country_id", "currency_id"])
print("Company:", company)

wanted = ["crm", "sale", "purchase", "stock", "account", "l10n_ae"]
mods = call("ir.module.module", "search_read",
            [("name", "in", wanted)], fields=["name", "state"])
for m in sorted(mods, key=lambda x: x["name"]):
    print(f"  {m['name']}: {m['state']}")
