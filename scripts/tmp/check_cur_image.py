import sqlite3
UUID = '4349fdad-a273-450b-aa00-3d32f2de788d'
DB = '/var/lib/docker/volumes/larapaper_database/_data/database.sqlite'
conn = sqlite3.connect(DB)
uuid = conn.execute("SELECT current_image FROM plugins WHERE uuid=?", (UUID,)).fetchone()
print(uuid[0])
conn.close()
