import gspread
from gspread_formatting import cellFormat, color, textFormat, format_cell_range, set_frozen
import datetime

class SheetsManager:
    def __init__(self, credentials_path, sheet_url):
        print("[Sheets] Authenticating with Google APIs...")
        self.gc = gspread.service_account(filename=credentials_path)
        print(f"[Sheets] Connecting to Spreadsheet...")
        self.sh = self.gc.open_by_url(sheet_url)
        self.setup_tabs()

    def setup_tabs(self):
        """Auto-provisions the required tabs with beautiful formatting."""
        # 1. Settings Tab
        try:
            self.ws_settings = self.sh.worksheet("Settings")
        except gspread.exceptions.WorksheetNotFound:
            print("[Sheets] Creating 'Settings' tab...")
            self.ws_settings = self.sh.add_worksheet(title="Settings", rows="20", cols="4")
            self.ws_settings.update('A1:B2', [['Setting', 'Value'], ['JINA_API_KEY', '']])
            self._format_header(self.ws_settings, "A1:B1", bg_color=(0.16, 0.5, 0.73)) # Blue
            
        # 2. Extracted Data Tab
        try:
            self.ws_data = self.sh.worksheet("Extracted JSON")
        except gspread.exceptions.WorksheetNotFound:
            print("[Sheets] Creating 'Extracted JSON' tab...")
            self.ws_data = self.sh.add_worksheet(title="Extracted JSON", rows="1000", cols="5")
            self.ws_data.update('A1:E1', [['Timestamp', 'Domain', 'Status', 'Jina JSON Output', 'Notes']])
            self._format_header(self.ws_data, "A1:E1", bg_color=(0.18, 0.8, 0.44)) # Green
            
        # Delete default Sheet1 if exists
        try:
            sheet1 = self.sh.worksheet("Sheet1")
            self.sh.del_worksheet(sheet1)
        except:
            pass
            
        print("[Sheets] All tabs configured and formatted!")

    def _format_header(self, ws, range_name, bg_color):
        fmt = cellFormat(
            backgroundColor=color(*bg_color),
            textFormat=textFormat(bold=True, foregroundColor=color(1, 1, 1)),
            horizontalAlignment='CENTER'
        )
        format_cell_range(ws, range_name, fmt)
        set_frozen(ws, rows=1)

    def get_jina_api_key(self):
        """Reads the API key live from the cloud."""
        try:
            val = self.ws_settings.acell('B2').value
            return val if val else None
        except:
            return None

    def set_jina_api_key(self, api_key):
        """Updates the API key cell in the sheet."""
        try:
            self.ws_settings.update_acell('B2', api_key)
            print("[Sheets] Jina API Key synced to the cloud successfully.")
        except Exception as e:
            print(f"[Sheets Error] Could not update API Key in sheet: {e}")

    def append_extracted_data(self, domain, json_output, status="SUCCESS"):
        """Appends a new row of scraped data to the sheet."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.ws_data.append_row([timestamp, domain, status, json_output, ""])
        except Exception as e:
            print(f"[Sheets Error] Failed to write {domain} to sheet: {e}")
