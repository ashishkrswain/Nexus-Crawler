import sqlite3
import csv
import os

def export_to_csv(db_path="data/nexus.db", csv_path="data/nexus_export.csv"):
    if not os.path.exists(db_path):
        print(f"Error: Database {db_path} does not exist. Run the crawler first!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, domain, discovered_at, status FROM scraped_companies")
    rows = cursor.fetchall()
    
    if not rows:
        print("The database is empty. Nothing to export.")
        conn.close()
        return

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Domain", "Discovered At", "Status"])
        writer.writerows(rows)
        
    conn.close()
    print(f"Successfully exported {len(rows)} domains to {csv_path}!")
    print("You can easily open this file in Google Sheets.")

if __name__ == "__main__":
    export_to_csv()
