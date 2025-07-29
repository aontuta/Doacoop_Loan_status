import oracledb
import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials

# --- Oracle DB Config ---
db_config = {
    "user": os.environ.get("ORACLE_USER"),
    "password": os.environ.get("ORACLE_PASS"),
    "dsn": os.environ.get("ORACLE_DSN")
}

# --- Google Sheet Setup ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("LoanStatus API").worksheet("DB")
sheet.clear()

# --- SQL Query ---
sql = "SELECT 'ตัวอย่าง' AS example_column FROM dual"

# --- Run Query and Write to Sheet ---
with oracledb.connect(**db_config) as conn:
    with conn.cursor() as cursor:
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

sheet.append_row(columns)
for row in rows:
    sheet.append_row(list(row))
