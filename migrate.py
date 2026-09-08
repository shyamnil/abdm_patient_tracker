import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

columns = [
    ("doctor_suggestion", "TEXT DEFAULT 'Awaiting doctor consultation.'"),
    ("doctor_name", "TEXT DEFAULT 'N/A'"),
    ("hospital_name", "TEXT DEFAULT 'N/A'")
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE patient_problems ADD COLUMN {col_name} {col_type}")
        print(f"Added column: {col_name}")
    except sqlite3.OperationalError as e:
        print(f"Column {col_name} status: {e}")

conn.commit()
conn.close()