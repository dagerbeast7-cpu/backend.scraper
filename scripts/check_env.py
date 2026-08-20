import os
import sys

print("DATABASE_URL set:", bool(os.environ.get("DATABASE_URL")))
print("SUPABASE_KEY set:", bool(os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")))
