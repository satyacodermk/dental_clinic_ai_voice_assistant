import sqlite3
import os
from datetime import datetime

# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------
BASE_DIR = r".\db"
DB_FOLDER = os.path.join(BASE_DIR, "db_files")
DB_PATH = os.path.join(DB_FOLDER, "dental_care_clinic.db")

# -------------------------------------------------------------------
# Ensure db_files folder exists
# -------------------------------------------------------------------
os.makedirs(DB_FOLDER, exist_ok=True)

# -------------------------------------------------------------------
# Connect to the database (creates file if not exists)
# -------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# -------------------------------------------------------------------
# Create tables
# -------------------------------------------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) DEFAULT '',
    phone_no VARCHAR(15) NOT NULL,
    age INTEGER CHECK(age >= 0 AND age <= 120) NOT NULL,
    gender VARCHAR(10) CHECK(gender IN ('Male', 'Female', 'Other')) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    reason VARCHAR(200) NOT NULL,
    status VARCHAR(20) CHECK(status IN ('Scheduled', 'Completed', 'Cancelled')) DEFAULT 'Scheduled',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);
""")

# -------------------------------------------------------------------
# Insert sample client data
# -------------------------------------------------------------------
clients_data = [
    ("Rohit", "Sharma", "rohit.sharma@example.com", "+91-9876543210", 32, "Male", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ("Priya", "Verma", "priya.verma@example.com", "+91-9123456780", 28, "Female", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ("Arjun", "Patel", "", "+91-9988776655", 40, "Male", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
]

cursor.executemany("""
INSERT INTO clients (first_name, last_name, email, phone_no, age, gender, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", clients_data)

# -------------------------------------------------------------------
# Fetch client IDs for sample appointments
# -------------------------------------------------------------------
cursor.execute("SELECT client_id, first_name FROM clients")
clients = cursor.fetchall()

# Insert sample appointments
appointments_data = [
    (clients[0][0], "2025-11-05", "10:00", "Routine Dental Checkup", "Scheduled"),
    (clients[1][0], "2025-11-06", "11:30", "Tooth Cleaning", "Scheduled"),
    (clients[2][0], "2025-11-07", "14:00", "Root Canal Consultation", "Scheduled")
]

cursor.executemany("""
INSERT INTO appointments (client_id, appointment_date, appointment_time, reason, status)
VALUES (?, ?, ?, ?, ?)
""", appointments_data)

# -------------------------------------------------------------------
# Commit and close
# -------------------------------------------------------------------
conn.commit()
conn.close()

print(f"✅ Database created successfully at:\n{DB_PATH}")
print("✅ Tables 'clients' and 'appointments' created with proper data types.")
print("✅ Sample data inserted successfully.")
