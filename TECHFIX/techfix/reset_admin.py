"""Reset admin password to allow login"""
import sqlite3
import sys
import os

# Find the database file
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'techfix.sqlite3')
if not os.path.exists(db_path):
    db_path = os.path.join(os.path.dirname(__file__), 'techfix.sqlite3')

print(f"Database path: {db_path}")

if not os.path.exists(db_path):
    print("ERROR: Database file not found!")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

try:
    # Check current admin user
    cur = conn.execute("SELECT id, username, password_hash, is_active FROM users WHERE username='admin'")
    row = cur.fetchone()
    
    if row:
        print(f"\nCurrent admin user:")
        print(f"  ID: {row['id']}")
        print(f"  Username: {row['username']}")
        print(f"  Password Hash: {row['password_hash']}")
        print(f"  Active: {row['is_active']}")
        
        # Reset password hash to NULL
        conn.execute("UPDATE users SET password_hash = NULL WHERE username='admin'")
        conn.commit()
        print("\n✓ Password hash reset to NULL")
        print("  You can now login with username='admin' and password='admin'")
        print("  The password will be set on first successful login.")
    else:
        print("\nERROR: Admin user not found!")
        print("Creating admin user...")
        
        # Get role and company
        role_cur = conn.execute("SELECT id FROM roles WHERE name='Admin'")
        role_row = role_cur.fetchone()
        role_id = role_row['id'] if role_row else None
        
        company_cur = conn.execute("SELECT id FROM companies WHERE code='DEFAULT'")
        company_row = company_cur.fetchone()
        company_id = company_row['id'] if company_row else None
        
        if role_id and company_id:
            conn.execute(
                "INSERT INTO users(username, full_name, role_id, company_id, is_active, password_hash) VALUES (?, ?, ?, ?, 1, NULL)",
                ('admin', 'Administrator', role_id, company_id)
            )
            conn.commit()
            print("✓ Admin user created with NULL password hash")
        else:
            print(f"ERROR: Role ID={role_id}, Company ID={company_id}")
            print("Please run the application first to initialize the database.")
    
    conn.close()
    print("\nDone!")
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

