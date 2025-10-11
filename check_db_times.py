#!/usr/bin/env python3
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import db

# Query recent attendance records
query = """
SELECT
    id, user_id, date,
    entry_time, exit_time,
    total_hours, status,
    entry_time AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata' as entry_ist,
    exit_time AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Kolkata' as exit_ist
FROM attendance
ORDER BY date DESC, entry_time DESC
LIMIT 5
"""

print("Recent attendance records from database:")
print("=" * 80)
with db.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        if rows:
            for row in rows:
                print(f"\nID: {row[0]}")
                print(f"User ID: {row[1]}")
                print(f"Date: {row[2]}")
                print(f"Entry Time (stored): {row[3]}")
                print(f"Exit Time (stored): {row[4]}")
                print(f"Total Hours: {row[5]}")
                print(f"Status: {row[6]}")
                print(f"Entry Time (IST): {row[7]}")
                print(f"Exit Time (IST): {row[8]}")
                print("-" * 80)
        else:
            print("No attendance records found")

# Check PostgreSQL timezone setting
cur.execute("SHOW timezone;")
tz = cur.fetchone()
print(f"\nPostgreSQL timezone setting: {tz[0]}")
