import sqlite3, os, sys

TEMPLATE_PATH = '/tmp/ha_dashboard_full.liquid'
DB_PATH = '/var/lib/docker/volumes/larapaper_database/_data/database.sqlite'
UUID = '4349fdad-a273-450b-aa00-3d32f2de788d'

if not os.path.exists(TEMPLATE_PATH):
    print('ERROR: Template not found at ' + TEMPLATE_PATH)
    sys.exit(1)

with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    template = f.read()

print('Template size: ' + str(len(template)) + ' bytes')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

plugin = conn.execute(
    'SELECT id, name, length(render_markup) as old_len FROM plugins WHERE uuid = ?',
    (UUID,)
).fetchone()

if not plugin:
    print('ERROR: Plugin not found')
    sys.exit(1)

print('Plugin: ' + plugin['name'] + ' (id=' + str(plugin['id']) + ')')
print('Old render_markup: ' + str(plugin['old_len']) + ' bytes')
print('New render_markup: ' + str(len(template)) + ' bytes')

conn.execute(
    'UPDATE plugins SET render_markup = ?, updated_at = datetime("now") WHERE id = ?',
    (template, plugin['id'])
)
conn.commit()

updated = conn.execute(
    'SELECT length(render_markup) FROM plugins WHERE id = ?',
    (plugin['id'],)
).fetchone()
print('Updated: ' + str(updated[0]) + ' bytes')
conn.close()
print('Template deployed to LaraPaper.')
