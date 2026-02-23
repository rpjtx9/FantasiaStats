from database import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT pa.exp_gained 
    FROM player_activity pa
    JOIN snapshots s ON pa.snapshot_id = s.id
    WHERE pa.name = 'Lide'
    ORDER BY s.timestamp
""")
for row in cursor.fetchall():
    print(row[0])
conn.close()