"""
Teste local sem postar de verdade.
Uso:
    python scripts/dry_run.py
"""
import os
os.environ["DRY_RUN"] = "true"
from post_to_instagram import main
raise SystemExit(main())
