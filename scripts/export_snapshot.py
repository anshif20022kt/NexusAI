import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))

from core import from_odoo, save_snapshot  # noqa: E402

data = from_odoo()
save_snapshot(data)
for name, df in data.items():
    print(f"  {name}: {len(df)} rows")
print("Snapshot saved to data/snapshot/")