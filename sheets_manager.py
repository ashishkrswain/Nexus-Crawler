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
            # Ensure the new rows exist for people upgrading from Phase 4
            if not self.ws_settings.acell('A3').value:
                self.ws_settings.update('A3:B4', [
                    ['Target_Industry', 'AI Startups'],
                    ['Target_Amount', '10']
                ])
        except gspread.exceptions.WorksheetNotFound:
            print("[Sheets] Creating 'Settings' tab...")
            self.ws_settings = self.sh.add_worksheet(title="Settings", rows="20", cols="4")
            self.ws_settings.update('A1:B4', [
                ['Setting', 'Value'], 
                ['JINA_API_KEY', ''],
                ['Target_Industry', 'AI Startups'],
                ['Target_Amount', '10']
            ])
            self._format_header(self.ws_settings, "A1:B1", bg_color=(0.16, 0.5, 0.73)) # Blue
            
        # Delete default Sheet1 if exists
        try:
            sheet1 = self.sh.worksheet("Sheet1")
            self.sh.del_worksheet(sheet1)
        except:
            pass

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

    def get_settings(self):
        """Reads industry and amount settings."""
        try:
            industry = self.ws_settings.acell('B3').value or "General Startups"
            amount = int(self.ws_settings.acell('B4').value or 10)
            return str(industry), amount
        except:
            return "General Startups", 10

    def create_batch_tab(self, industry, data_rows):
        """Creates a new tab for the finished batch and writes all data."""
        date_str = datetime.datetime.now().strftime("%b%d")
        amount = len(data_rows)
        # Clean tab name
        tab_name = f"{str(industry)[:15]}_{date_str}_{amount}".replace(" ", "_").replace(".", "")
        
        try:
            ws = self.sh.add_worksheet(title=tab_name, rows=str(max(100, amount+10)), cols="5")
            ws.update('A1:E1', [['Timestamp', 'URL', 'Status', 'Jina JSON Output', 'Notes']])
            self._format_header(ws, "A1:E1", bg_color=(0.6, 0.2, 0.8)) # Purple
            
            if data_rows:
                ws.append_rows(data_rows)
            print(f"[Sheets] Successfully created and populated batch tab: {tab_name}")
            return tab_name
        except Exception as e:
            print(f"[Sheets Error] Could not create batch tab: {e}")
            return None
