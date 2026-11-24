import os
import xmlrpc.client
import getpass

from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("ODOO_URL", "http://localhost:8069")
DB = os.getenv("ODOO_DB", "nexusai")


class Odoo:
    def __init__(self):
        email = os.getenv("ODOO_EMAIL") or input("Odoo admin email: ")
        self.password = os.getenv("ODOO_PASSWORD") or getpass.getpass("Odoo admin password: ")
        common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        self.uid = common.authenticate(DB, email, self.password, {})
        if not self.uid:
            raise SystemExit("LOGIN FAILED: check the values in your .env file")
        self.models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(self, model, method, *args, **kwargs):
        try:
            return self.models.execute_kw(
                DB, self.uid, self.password, model, method, list(args), kwargs
            )
        except xmlrpc.client.Fault as e:
            # Some Odoo actions return nothing; the action itself succeeded.
            if "cannot marshal None" in str(e):
                return None
            raise

    def find(self, model, domain):
        ids = self.call(model, "search", domain, limit=1)
        return ids[0] if ids else None