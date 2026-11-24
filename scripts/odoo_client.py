import xmlrpc.client
import getpass

URL = "http://localhost:8069"
DB = "nexusai"


class Odoo:
    def __init__(self):
        email = input("Odoo admin email: ")
        self.password = getpass.getpass("Odoo admin password: ")
        common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        self.uid = common.authenticate(DB, email, self.password, {})
        if not self.uid:
            raise SystemExit("LOGIN FAILED: check email and password")
        self.models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(self, model, method, *args, **kwargs):
        try:
            return self.models.execute_kw(
                DB, self.uid, self.password, model, method, list(args), kwargs
            )
        except xmlrpc.client.Fault as e:
            # Some Odoo actions return nothing. The action itself succeeded;
            # only the empty reply cannot be sent back over XML-RPC.
            if "cannot marshal None" in str(e):
                return None
            raise

    def find(self, model, domain):
        ids = self.call(model, "search", domain, limit=1)
        return ids[0] if ids else None
