"""Inspect existing prospects in PostgreSQL and report phone status with safe encoding."""
import os
import sys
import psycopg2
import phonenumbers

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.euvcqzmwezarbdgpfszq:dagerbeast300k@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

cur.execute("""
    SELECT id, business_name, contact_name, phone, city, locality, status, score, created_at
    FROM prospects
    ORDER BY score DESC, created_at ASC;
""")
rows = cur.fetchall()

no_phone_leads = []
with_phone_leads = []

for idx, r in enumerate(rows, 1):
    pid, bname, cname, phone, city, loc, status, score, cat = r
    
    is_usable = False
    if phone:
        try:
            parsed = phonenumbers.parse(phone, "IN")
            if phonenumbers.is_valid_number(parsed):
                is_usable = True
        except Exception:
            is_usable = False
            
    if is_usable:
        with_phone_leads.append(r)
    else:
        no_phone_leads.append(r)

print(f"TOTAL PROSPECTS IN DATABASE: {len(rows)}")
print(f"WITH USABLE PHONE: {len(with_phone_leads)}")
print(f"WITHOUT USABLE PHONE: {len(no_phone_leads)}")
print("=" * 100)

if no_phone_leads:
    print(f"\nLIST OF {len(no_phone_leads)} PROSPECTS WITHOUT A USABLE PHONE NUMBER:")
    print("-" * 100)
    for idx, r in enumerate(no_phone_leads, 1):
        bname = (r[1] or "").encode("ascii", "replace").decode("ascii")
        city = (r[4] or "").encode("ascii", "replace").decode("ascii")
        loc = (r[5] or "").encode("ascii", "replace").decode("ascii")
        phone = r[3]
        print(f"  {idx:>3}. {bname:<45} | City: {city:<12} | Locality: {loc:<15} | Raw Phone: {phone}")

conn.close()
