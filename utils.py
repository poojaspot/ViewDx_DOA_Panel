from tinydb import TinyDB, Query
import tkinter as tk
from tkinter import filedialog
import subprocess
from datetime import datetime
import numpy as np
from pyzbar.pyzbar import decode
import time
import importlib
import shutil
import webbrowser
import widgets
import exitprocess
import deviceinfo
import os
import json
import csv
import results
import imagepro
import re
import traceback


def get_pendrive():
    try:
        result = subprocess.run(
            ["lsblk", "-o", "NAME,MOUNTPOINT", "-nr"],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                device_name, mountpoint = parts
                if mountpoint.startswith("/media") or "/media" in mountpoint:
                    device_path = f"/dev/{device_name}"
                    subprocess.run(["sudo", "fatlabel", device_path, "VIEWDX"], check=False)
                    return mountpoint
    except Exception as e:
        widgets.error("Error detecting pendrive")
        results.usesummary(f"Error detecting pendrive: {e}")
        return None

def addcsv():
    pendrive = get_pendrive()
    if not pendrive:
        widgets.error("Please insert pendrive")
        return

    filename = filedialog.askopenfilename(
        initialdir=pendrive,
        title="Select a CSV File",
        filetypes=(("CSV files", "*.csv"),)
    )

    if not filename:
        widgets.error("No file selected.")
        return

    # Load database
    analytedb = TinyDB(deviceinfo.path + 'analytes.json')
    Sample = Query()

    success_count = 0
    fail_count = 0

    try:
        with open(filename, mode='r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                if not row.get('analyte'):
                    continue  # skip empty lines or malformed rows

                try:
                    record = {
                        "analyte": row['analyte'].strip(),
                        "calid": row['calid'].strip(),
                        "caldate": row['caldate'].strip(),
                        "expdate": row['expdate'].strip(),
                        "batchid": row['batchid'].strip(),
                        "measl": row['measl'].strip(),
                        "measu": row['measu'].strip(),
                        "unit": row['unit'].strip()
                    }
                    analytedb.insert(record)
                    success_count += 1
                except Exception as row_error:
                    fail_count += 1
                    results.usesummary(f"Analyte csv row update error: {row_error}")
                    continue
    except Exception as file_error:
        widgets.error(f"Failed to read file: {file_error}")
        results.usesummary(f"CSV Read Error: {file_error}")
        return

    if success_count > 0:
        widgets.error(f"{success_count} analytes were added.\nCheck the analytes table to avoid duplication.")
    if fail_count > 0:
        widgets.error(f"{fail_count} rows failed to upload. Please check the CSV file format.")


def csv_gencal(conc_array, result_array):
    pendrive = get_pendrive()
    if not pendrive: widgets.error("Please insert pendrive")
    filename = filedialog.askopenfilename(initialdir = ('/media/pi/VIEWDX'), title = "Select a File", filetypes = (("data files","*.csv"),))
    with open(filename, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            print(row)
            conc_array=np.append(conc_array, float(row['Conc']))
            result_array=np.append(result_array, float(row['Result']))

    results.usesummary("Data added from CSV file for generation of Calid")
    return conc_array, result_array

def results_backup():
    sys_time = str(datetime.now().replace(microsecond=0))
    date = datetime.now().strftime('%y-%m-%d')
    src_folder = os.path.join(deviceinfo.path, 'results')

    if not os.path.exists(src_folder):
        widgets.error("Results folder not found.")
        return

    try:
        pendrive = get_pendrive()
    except Exception as e:
        widgets.error(f"Error detecting pendrive: {e}")
        results.usesummary(str(e))
        return

    if not pendrive:
        widgets.error("Please insert pendrive labeled 'VIEWDX'")
        return

    dst_folder = os.path.join(pendrive, f"backup_{date}")

    try:
        subprocess.run(["sudo", "mkdir", "-p", dst_folder], check=True)
        subprocess.run(["sudo", "cp", "-r", src_folder, dst_folder], check=True)
        updatedeviceinfo("backup_time", deviceinfo.backup_time, sys_time)
        widgets.error("Backup complete.")
    except subprocess.CalledProcessError as e:
        widgets.error(f"Backup failed: {e}")
        results.usesummary(str(e))
    except Exception as e:
        widgets.error(f"Unexpected error: {e}")
        results.usesummary(str(e))


def browseFiles(path, filetype):
    filename = filedialog.askopenfilename(
        initialdir=path,
        title="Select a File",
        filetypes=(("Files", filetype),)
    )
    if not filename:
        widgets.error("No file selected.")
        return

    try:
        webbrowser.open_new(filename)
    except Exception as e:
        widgets.error(f"Failed to open file: {e}")
        results.usesummary(str(e))


def exportFiles(path):
    filename = filedialog.askopenfilename(
        initialdir=path,
        title="Select a File",
        filetypes=(("PDF files", "*.pdf"),)
    )
    if not filename:
        widgets.error("No file selected.")
        return

    try:
        pendrive = get_pendrive()
        if not pendrive:
            widgets.error("Please insert pendrive.")
            return

        dest_path = os.path.join(pendrive, os.path.basename(filename))
        subprocess.run(["sudo", "cp", filename, dest_path], check=True)
        widgets.error(f"File successfully copied to {pendrive}.")
    except subprocess.CalledProcessError as e:
        widgets.error(f"Copy failed: {e}")
        results.usesummary(str(e))
    except Exception as e:
        widgets.error(f"Unexpected error: {e}")
        results.usesummary(str(e))
def restore():
    global msg
    path = deviceinfo.path + 'results/'
    pendrive = get_pendrive() 
    if not pendrive:
        widgets.error("Please insert pendrive and try again")
    else:
        src_folder = filedialog.askdirectory(title = "Select the folder", initialdir = pendrive)
        dst_folder = path
        counter = 0
        merge_result_json(src_folder,dst_folder)
        while True:
            if not os.listdir(src_folder):
                widgets.error("Selected folder is empty")
            break
        for filename in os.listdir(src_folder):
            src_item = os.path.join(src_folder, filename)
            if os.path.basename(src_item) not in os.listdir(dst_folder):
                subprocess.run(["sudo", "cp", "-r", src_item, dst_folder])
            else:
                counter += 1
        if counter != 0:
            msg = str(counter)  + 'reports already exist, all other files are copied '
        else:
            msg = "Results are restored"
        widgets.error(msg)
                
def merge_result_json(src_folder,dst_folder):
    result_file ="results.json"
    src_path = os.path.join(src_folder,result_file)
    dst_path = os.path.join(dst_folder, result_file)

    if not os.path.exists(src_path) or not os.path.exists(dst_path):
        msg = "results.json is missing in pendrive"
        widgets.error(msg)
    else:
        with open(src_path, 'r')as src_f, open(dst_path, 'r') as dst_f:
            src_data = json.load(src_f)
            dst_data = json.load(dst_f)
        for key, value in src_data.items():
            if key not in dst_data:
                dst_data[key] = value
        with open(dst_path, 'w') as merg_f:
            json.dump(dst_data, merg_f, indent = 4)

def update_file_from_pendrive(filetype_desc, extension, dst_filename, success_msg):
    pendrive = get_pendrive()
    if not pendrive:
        widgets.error("Please insert pendrive.")
        return

    filename = filedialog.askopenfilename(
        initialdir=pendrive,
        title="Select a File",
        filetypes=((filetype_desc, extension),)
    )

    if not filename:
        widgets.error(f"No {filetype_desc.lower()} selected.")
        return

    dst_path = os.path.join(deviceinfo.path, dst_filename)

    if not os.path.isfile(filename):
        widgets.error("Selected file does not exist.")
        return

    try:
        subprocess.run(["sudo", "cp", filename, dst_path], check=True)
        widgets.error(success_msg)
    except subprocess.CalledProcessError as e:
        widgets.error(f"Failed to copy file: {e}")
        results.usesummary(str(e))
    except Exception as e:
        widgets.error(f"Unexpected error: {e}")
        results.usesummary(str(e))


def sigupdate(string=None):
    update_file_from_pendrive(
        filetype_desc="Signature",
        extension="*.png",
        dst_filename="signature.png",
        success_msg="New Signature Added"
    )


def logoupdate(string=None):
    update_file_from_pendrive(
        filetype_desc="Logo",
        extension="*.png",
        dst_filename="lab_logo.png",
        success_msg="New Logo Added"
    )

def update():
    path = deviceinfo.path.rstrip('/')
    try:
        # Rename current folder by appending count
        num_items = len(os.listdir(path))
        new_folder_name = f"{path}{num_items + 1}"
        
        os.rename(path, new_folder_name)
        backup_dir = "/home/pi/prev_viewdx"
        
        os.makedirs(backup_dir, exist_ok=True)
        shutil.move(new_folder_name, backup_dir)

    except Exception as e:
        widgets.error(f"Backup failed: {str(e)}")
        results.usesummary(str(e))
        widgets.error("Could not move previous version")

    try:
        def new_version(dst_path):
            pendrive = get_pendrive()
            if not pendrive:
                widgets.error("Please insert pendrive.")
                return
            src_file = os.path.join(pendrive, "viewdx.py")
            if not os.path.isfile(src_file):
                widgets.error("Update file 'viewdx.py' not found on pendrive.")
                return
            shutil.copy(src_file, dst_path)
            widgets.error("Software updated successfully.")

        widgets.askquestion("Update Software?", new_version, path)

    except Exception as e:
        widgets.error(f"Update failed: {str(e)}")
        results.usesummary(str(e))
        widgets.error("Could not update software")

def update_from_cloud(cloud_folder):
    project_root = deviceinfo.path
    excluded_files = {
        'deviceinfo.py',
        'analytes.json',
        'splash_logo.png',
        'signature.png',
        'logo.png',
        'lab_logo.png'
    }

    excluded_folders = {'hardwaretest', 'usesummary', 'captured', 'results'}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = f"{project_root}/backup_{timestamp}"

    def should_copy(rel_path):
        filename = rel_path.split('/')[-1]
        if filename in excluded_files:
            return False

        if rel_path.startswith('viewdx/'):
            parts = rel_path.split('/')
            if len(parts) > 1 and parts[1] in excluded_folders:
                return False
        return True

    def backup_file(target_path):
        try:
            rel_path = target_path.replace(project_root + '/', '')
            backup_path = f"{backup_root}/{rel_path}"
            backup_dir = '/'.join(backup_path.split('/')[:-1])

            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            shutil.copy2(target_path, backup_path)
            print(f"Backed up: {rel_path}")
        except Exception as e:
            print(f"Backup failed for {target_path}: {e}")

    for root, dirs, files in os.walk(cloud_folder):
        rel_root = os.path.relpath(root, cloud_folder)
        if rel_root == '.':
            rel_root = ''

        target_root = f"{project_root}/{rel_root}" if rel_root else project_root

        dirs[:] = [
            d for d in dirs
            if not (rel_root.startswith('viewdx') and d in excluded_folders)
        ]

        # Ensure target directories exist
        for d in dirs:
            target_dir = f"{target_root}/{d}"
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

        for file in files:
            rel_file_path = f"{rel_root}/{file}" if rel_root else file
            if should_copy(rel_file_path):
                src_file = f"{root}/{file}"
                dst_file = f"{target_root}/{file}"

                # Backup before overwrite
                if os.path.exists(dst_file):
                    backup_file(dst_file)

                try:
                    shutil.copy2(src_file, dst_file)
                    widgets.error(f"Updated: {rel_file_path}")
                    results.usesummary(f"Updated: {rel_file_path}")
                    exitprocess.restart()
                except Exception as e:
                    widgets.error(f"Failed to update {rel_file_path}: {e}")
                    results.usesummary(f"Failed to update {rel_file_path}: {e}")
    results.usesummary(f"Update from cloud complete. Backup stored in: {backup_root}")


def check_format(date_str, time_str):
    if not date_str or not time_str:
        widgets.error("Please add the date and time")
        return 0, 

    try:
        datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
        return 1, ""
    except ValueError:
        widgets.error("Date-time format is not correct")
        return 0 

def change_time(dateE, timeE):
    date_str = dateE.get()
    time_str = timeE.get()
    print(date_str,time_str)

    # Validate format
    is_valid, msg = check_format(date_str, time_str)
    if not is_valid:
        widgets.error(msg)
        return
    try:
        # Validate full datetime
        dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        rtc_cmd = '"'+dt_str+'"'
        res = subprocess.run(["sudo", "hwclock", "--set", "--date", rtc_cmd],shell = True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,text= True)
        # Set system time
        subprocess.run(["sudo", "date", "-s", f"{dt.strftime('%Y-%m-%d %H:%M:%S')}"], check=True)
        widgets.error(f"System time is updated") 
    except ValueError as ve:
        print(ve)
        widgets.error(f"Invalid input: {ve}")
        results.usesummary(str(ve))
    except Exception as e:
        widgets.error(f"Unexpected error: {e}")
        results.usesummary(str(e))
    
def connectvpn():
    service_name = "vncserver-x11-serviced"

    try:
        if deviceinfo.remoteconnect == "Enabled":
            subprocess.run(
                ["sudo", "systemctl", "start", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            widgets.error("VNC Connected")
        else:
            subprocess.run(
                ["sudo", "systemctl", "stop", service_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            print("disconnected")
            widgets.error("VNC Disconnected")
        exitprocess.restart()

    except subprocess.CalledProcessError as e:
        widgets.error(f"Failed to {'start' if deviceinfo.remoteconnect == 'Enabled' else 'stop'} VNC service: {e.stderr.strip()}")
        results.usesummary(str(e))
    except Exception as e:
        widgets.error(str(e))
        results.usesummary(str(e))


def updatedeviceinfo(variable, old_string, new_string):
    try:
        filepath = deviceinfo.path + 'deviceinfo.py'
        with open(filepath, 'r') as f:
            lines = f.readlines()
        updated = False
        new_lines = []
        for line in lines:
            if variable in line and old_string in line:
                print(f"Old line: {line.strip()}")
                newline = line.replace(old_string, str(new_string))
                print(f"New line: {newline.strip()}")
                new_lines.append(newline)
                updated = True
            else:
                new_lines.append(line)

        if updated:
            with open(filepath, 'w') as f:
                f.writelines(new_lines)
            
            importlib.reload(deviceinfo)
        else:
            widgets.error(f"No matching line found containing '{variable}' and '{old_string}'")

    except Exception as e:
        widgets.error(str(e))
        results.usesummary(str(e))
        widgets.error('Unexpected error during writing deviceinfo')

def ping(ssid):
    command = ["ping", "-c", "1", "8.8.8.8"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    if result.returncode == 0:
        widgets.error(f"Successfully connected to {ssid}")
    else:
        widgets.error("Check password or try connecting to another network")

def togglewifi(state):
    try:
        if state == "Enabled":
            subprocess.run(["rfkill", "unblock", "wifi"], check=True)  # unblock wifi to enable
            print('wifi unblocked (enabled)')
        elif state == "Disabled":
            subprocess.run(["rfkill", "block", "wifi"], check=True)  # block wifi to disable
            print('wifi blocked (disabled)')
        else:
            widgets.error("Invalid wifi state. Use 'Enabled' or 'Disabled'.")
    except Exception as e:
        widgets.error(f"Error toggling wifi: {e}")

def list_wifi():
    try:
        s = subprocess.run(["rfkill", "list", "wifi"], capture_output=True, text=True, check=True).stdout
        if "Soft blocked: yes" in s:
            subprocess.run(["rfkill", "unblock", "wifi"], check=True)

        time.sleep(1)
        command = "sudo iwlist wlan0 scan | grep ESSID"
        process = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        output = process.stdout

        wifi_list = [line.strip().replace('ESSID:', '').replace('"', '') for line in output.splitlines()]
        return wifi_list

    except subprocess.CalledProcessError as e:
        widgets.error("Failed to scan wifi networks.")
        print(e)
        return []

def connect_wifi(ssid,password):
    try:
        subprocess.run(["sudo","rfkill","unblock","wifi"],check=True)
        time.sleep(2)
        command =["sudo", "nmcli","device","wifi","connect",ssid,"password",password]
        result = subprocess.run(command,capture_output=True,text=True,check=False)
        if result.returncode==0:
            print(f"successfully connected to {ssid}")
        else:
            print(result.stder)
    except FileNotFoundError:
        print("nmcli, rfcommand not found")
    except subprocess.CalledProcessError as e:
        print(f"error occured whillle running: {e}")
    except exception as e:
        print(e)

def update_wifi(ssidE, wpassE):
    try:
        ssid = ssidE.get().strip()
        #should i add back the Essid prefix here
        password = wpassE.get().strip()
        print(f"ssid is {ssid}")
        print(f"password is {password}")
        if not ssid or not password:
            widgets.error("Please add both SSID and password")
        else:
            connect_wifi(ssid, password)
            time.sleep(5)
    except Exception as e:
        widgets.error(f"Could not connect wifi: {e}")
        results.usesummary(str(e))

def get_ip_add():
    try:
        output = subprocess.run(['ifconfig', 'wlan0'], stdout=subprocess.PIPE, text=True, check=True).stdout
        for line in output.split('\n'):
            if 'inet ' in line and 'inet6' not in line:
                ip_address = line.strip().split()[1]
                if ip_address != '127.0.0.1':
                    widgets.error(f"IP Address: {ip_address}")
                    return ip_address
        widgets.error("No valid IP address found.")
        return None
    except Exception as e:
        widgets.error(f"Error getting IP address: {e}")
        return None

def checkcaldate(date_str: str) -> bool:
    try:
        now = datetime.now()
        current_month = now.month
        current_year = now.year % 100  # last two digits of year

        # Parse date string
        month_str, year_str = date_str.split('/')
        month = int(month_str)
        year = int(year_str)

        # Convert both to comparable decimal year
        current_decimal = current_year + current_month / 12
        date_decimal = year + month / 12

        elapsed = current_decimal - date_decimal
        
        # Check valid month and elapsed time < 1 year but > 0, can be 0 too as being calibirated in the same month when added to the device
        if 1 <= month <= 12 and 0 <= elapsed < 1:
            return True
        else:
            widgets.error("Calibration date is invalid")
            return False
    except Exception as e:
        widgets.error(f"Error checking calibration date: {e}")
        return False


def checkcalid(calid_str: str) -> bool:
    try:
        parts = re.split(r'[/:]', calid_str)
        num_parts = [float(p) for p in parts]

        if ':' in calid_str:
            # Expect 7 parts and 1st and 5th parts equal to 1
            if len(num_parts) == 7 and num_parts[0] == 1 and num_parts[4] == 1:
                return True
            else:
                return False
        else:
            # If 3 to 6 parts and first part is between 1 and 4 inclusive
            if 3 <= len(num_parts) < 7 and num_parts[0] in {1, 2, 3, 4}:
                return True
            else:
                return False
    except Exception as e:
        results.usesummary(str(e))
        widgets.error("Calid string format is incorrect")
        return False

def analyte_check():
    analytedb = TinyDB(deviceinfo.path + 'analytes.json')
    Sample = Query()
    ana_list = analytedb.all()
    purged = []

    for ana in ana_list:
        if not check_cal_date(ana['caldate']):
            purged.append(ana['calid'])
            analytedb.remove(Sample.calid == ana['calid'])
            widgets.error(f"Entries for calid {ana['calid']} have been removed")

    if not purged:
        widgets.error("No calibration ids need to be removed")


def updatepara(analyte, calid, caldate, expdate, batchid, measl='', measu='', unit='', clinical_range='', interpretation=''):
    analytedb = TinyDB(deviceinfo.path + 'analytes.json')
    analyte_str = {
        "analyte": analyte,
        "calid": calid,
        "caldate": caldate,
        "expdate": expdate,
        "batchid": batchid,
        "measl": measl,
        "measu": measu,
        "unit": unit,
        "clinical_range": clinical_range,
        "interpretation": interpretation
    }
    analytedb.insert(analyte_str)
    widgets.error(f"Parameter for {analyte} with batchid {batchid} has been updated")
    results.usesummary(f"Parameter for {analyte} with batchid {batchid} has been updated")

def show_image(image):
    popup = tk.Toplevel()
    popup.title("Plot")
    image_label = tk.Label(popup, image = image)
    image_label.pack()
    

def json_to_csv(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        rows = []
        default_data = data.get("_default", {})
        for record_id, record_data in default_data.items():
            row = record_data.copy()
            rows.append(row)
        if not rows:
            print(rows)
            results.usesummary("No data found in results file during email routine")
            return None

        desired_order = [
            "analyte", "sampleid", "cal_id", "result", "unit",
            "date", "name", "gender", "age"
        ]
        csv_path = deviceinfo.path+"results/results.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=desired_order)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in desired_order})
        return csv_path

    except Exception as e:
        results.usesummary(f"Error converting JSON to CSV: {e}")
        traceback.print_exc()
        


def getbatchidqr():
    analyte = 0
    batchid = []
    try:
        try:image = imagepro.camcapture('qr', '',40)
        except Exception as e: print(e)
        detect = decode(image)
        string = [obj.data.decode('utf-8') for obj in detect]
        string = ''.join(string)
        print(string)
        if string:
            print(string)
            results.usesummary("QR code scanned and decoded for "+ string)
            analyte, calid, caldate, expdate, unit, batchid, measl, measu = string.split(';')
            print('analyte, calid, caldate, expdate, unit, batchid, measl, measu',analyte, calid, caldate, expdate, unit, batchid, measl, measu)
            if analyte == "HBA":
                analyte = "HbA1C"
        else: widgets.error("No QR code detected.")
    except Exception as e:
        print(e)
        widgets.error("Could not add analyte")
    return analyte, batchid


