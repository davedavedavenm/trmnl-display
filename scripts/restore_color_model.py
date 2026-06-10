#!/usr/bin/env python3
import sqlite3
import sys

DB_PATH = '/var/lib/docker/volumes/larapaper_database/_data/database.sqlite'

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check current values
        cursor.execute("SELECT colors, bit_depth, palette_id FROM device_models WHERE name = 'inky_impression_7_3'")
        row = cursor.fetchone()
        if not row:
            print("ERROR: inky_impression_7_3 device model not found in database.")
            sys.exit(1)

        colors, bit_depth, palette_id = row
        print(f"Current model settings: colors={colors}, bit_depth={bit_depth}, palette_id={palette_id}")

        if colors == 7 and bit_depth == 4 and palette_id == 6:
            print("Settings are already correct (7 colors, bit depth 4, palette 6). No update needed.")
            conn.close()
            return

        print("Restoring color model settings in database...")
        cursor.execute(
            "UPDATE device_models SET colors = 7, bit_depth = 4, palette_id = 6 WHERE name = 'inky_impression_7_3'"
        )
        conn.commit()

        # Verify
        cursor.execute("SELECT colors, bit_depth, palette_id FROM device_models WHERE name = 'inky_impression_7_3'")
        new_row = cursor.fetchone()
        print(f"Verified settings: colors={new_row[0]}, bit_depth={new_row[1]}, palette_id={new_row[2]}")

        conn.close()
        print("Database update completed successfully.")
    except Exception as e:
        print(f"ERROR updating database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
