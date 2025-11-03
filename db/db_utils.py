import sqlite3
import os
import traceback

def execute_query(query: str):
    """
    Executes any SQL query (SELECT / INSERT / UPDATE / DELETE / JOIN etc.)
    on the dental_care_clinic.db database.
    
    Designed for LLM-generated SQL queries where parameters are part of the query string.
    
    Args:
        query (str): Full SQL query as a string.
    
    Returns:
        list[tuple] | None: Results for SELECT queries, otherwise None.
    """
    DB_PATH = r".\db\db_files\dental_care_clinic.db"

    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at: {DB_PATH}")
        return None

    if not query or not isinstance(query, str):
        print("⚠️ Invalid query provided (must be a non-empty string).")
        return None

    connection = None
    cursor = None

    try:
        # Connect to SQLite
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        print(f"✅ Connected to database: {os.path.basename(DB_PATH)}")

        # Strip leading/trailing spaces
        clean_query = query.strip()
        print(f"🔹 Executing Query:\n{clean_query}\n")

        cursor.execute(clean_query)

        # Identify query type
        query_type = clean_query.split()[0].lower()

        if query_type == "select":
            results = cursor.fetchall()
            print(f"✅ SELECT executed successfully — {len(results)} record(s) fetched.")
            return results
        else:
            connection.commit()
            print(f"✅ {query_type.upper()} query executed successfully — changes committed.")
            return None

    except sqlite3.OperationalError as e:
        print(f"⚠️ Operational Error: {e}")
        traceback.print_exc()

    except sqlite3.IntegrityError as e:
        print(f"⚠️ Integrity Error (constraint violation): {e}")
        traceback.print_exc()

    except sqlite3.DatabaseError as e:
        print(f"⚠️ General Database Error: {e}")
        traceback.print_exc()

    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        traceback.print_exc()

    finally:
        # Always close connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("🔒 Database connection closed.\n")

    return None



# --- sample for testing -----------
if __name__=="__main__":
    # --------- 1️⃣ Find a specific client by first and last name ---
    # query = """
    # SELECT client_id, first_name, last_name, phone_no, email
    # FROM clients
    # WHERE first_name = 'Rohit' AND last_name = 'Sharma';
    # """

    # results = execute_query(query)
    # print(results)

    # # ---------- 2️⃣ Get all appointments for a given client (using client_id)--------------
    # query = """
    # SELECT a.appointment_id, a.appointment_date, a.appointment_time, a.reason, a.status
    # FROM appointments a
    # WHERE a.client_id = 1;
    # """
    # results = execute_query(query)
    # print(results)

    query = """
    SELECT 
        c.client_id,
        c.first_name,
        c.last_name,
        a.appointment_id,
        a.appointment_date,
        a.appointment_time,
        a.reason,
        a.status
    FROM clients c
    JOIN appointments a 
        ON c.client_id = a.client_id
    WHERE 
        LOWER(c.first_name) = LOWER('rohit')
        AND LOWER(c.last_name) = LOWER('sharma')
    ORDER BY a.appointment_date, a.appointment_time;
    """

    new_query = "SELECT appointments.* FROM appointments JOIN clients ON appointments.client_id = clients.client_id WHERE LOWER(clients.first_name) = 'rohit' AND LOWER(clients.last_name) = 'sharma';"
    results = execute_query(new_query)
    print(results)

    

