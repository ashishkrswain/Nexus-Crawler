import os
from dotenv import load_dotenv
from sheets_manager import SheetsManager

load_dotenv()

SHEET_URL = os.getenv("SHEET_URL")
CREDENTIALS_PATH = "/home/tracxn-lp-760/Downloads/dev/nim-sum/ashish_credentials.json"

def main():
    print("Connecting to Google Sheets...")
    try:
        sheets = SheetsManager(CREDENTIALS_PATH, SHEET_URL)
        print("Setup complete! Check your browser!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
