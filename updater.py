import os
import shutil
import subprocess
import zipfile
from datetime import datetime
import sys
import importlib.util
import time
import logging
import tkinter as tk
from tkinter import Label
import re
            
# Set up logging
log_dir = "/home/pi/logs"
os.makedirs(log_dir, exist_ok=True)
log_file_name = f"update {datetime.now().strftime('%Y%m%d_%H%M')}"
log_file = os.path.join(log_dir, log_file_name)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also log to console for real-time debugging
    ]
)
logger = logging.getLogger(__name__)

# Function to load a module from a file path
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Copy required modules to a temporary location and load them
temp_dir = "/tmp/viewdx_modules"
os.makedirs(temp_dir, exist_ok=True)

# List of required modules
required_modules = ["deviceinfo", "results", "widgets"]
module_paths = {}

try:
    for module_name in required_modules:
        src_path = os.path.join("/home/pi/viewdx", f"{module_name}.py")
        if os.path.exists(src_path):
            temp_path = os.path.join(temp_dir, f"{module_name}.py")
            shutil.copy2(src_path, temp_path)
            module_paths[module_name] = temp_path
        else:
            raise FileNotFoundError(f"Required module {module_name}.py not found in /home/pi/viewdx/")

    # Load the modules from the temporary location
    deviceinfo = load_module_from_path("deviceinfo", module_paths["deviceinfo"])
    results = load_module_from_path("results", module_paths["results"])
    widgets = load_module_from_path("widgets", module_paths["widgets"])

except Exception as e:
    logger.error(f"Failed to load required modules: {str(e)}")
    sys.exit(1)

def update(source_type="pendrive", source_path=None):
    """
    Updates the software from a pendrive (viewdx.zip) or Git repository, preserving protected files/folders
    and specific deviceinfo fields while updating software_version and comments from the new version.
    
    Args:
        source_type (str): Type of update source ('git' or 'pendrive')
        source_path (str, optional): Path to the pendrive or Git repository URL
    """
    logger.info("Starting update process")
    #create a small tkinter window for buffering msg
    root = tk.Tk()
    root.title("Update in Progress")
    root.geometry("400x100")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    root.grab_set()
    root.protocol("WM_DELETE_WINDOW", lambda:None)
    label = Label(root, text ="Do not switch off. \nUpdate in progress.", font = ("Arial",18),
                  fg = "red",justify = "center",pady = 20)
    label.pack(expand = True)
    root.update()
    logger.info("Displayed buffering UI: 'DO not switch off/ update in progress.'")
    

    # Add a small delay to ensure main.py has fully exited
    time.sleep(1)
    logger.info("Delay completed, proceeding with update")

    # Define protected files and folders
    protected_files = [
        "analytes.json", "lab_logo.png",
        "signature.png", "instructions.jpg"
    ]
    protected_folders = ["captured", "results", "usesummary", "hardwaretest"]

    # Get the current path from deviceinfo
    viewdx_path = deviceinfo.path  # /home/pi/viewdx/
    current_dir =  "/home/pi/viewdx" #os.getcwd()  # Should be /home/pi/viewdx/ when using viewdx path it gives error 
    temp_extract_dir = os.path.join(current_dir, "temp_extract")
    pre_viewdx_dir = "/home/pi/pre_viewdx"
    backup_name = f"viewdx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(pre_viewdx_dir, backup_name)

    # Step 1: Backup the current viewdx directory to /home/pi/pre_viewdx with date
    try:
        logger.info("Creating backup directory")
        # Ensure /home/pi/pre_viewdx exists
        os.makedirs(pre_viewdx_dir, exist_ok=True)

        # Remove any existing backup in /home/pi/pre_viewdx to ensure only one backup exists
        for item in os.listdir(pre_viewdx_dir):
            item_path = os.path.join(pre_viewdx_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
                logger.info(f"Removed old backup: {item_path}")

        # Copy the running updater.py to a temporary location to preserve it
        current_script = os.path.basename(__file__)  # e.g., "updater.py"
        temp_script_path = os.path.join("/tmp", current_script)
        shutil.copy2(os.path.join(current_dir, current_script), temp_script_path)
        logger.info(f"Copied running script to temporary location: {temp_script_path}")

        # Move the current viewdx directory to /home/pi/pre_viewdx/<backup_name>
        if os.path.exists(viewdx_path):
            shutil.move(viewdx_path, backup_path)
            logger.info(f"Moved current viewdx directory to backup: {backup_path}")

        # Recreate the viewdx directory
        os.makedirs(viewdx_path, exist_ok=True)
        logger.info(f"Recreated viewdx directory: {viewdx_path}")

        # Copy the running updater.py back into /home/pi/viewdx/
        shutil.copy2(temp_script_path, os.path.join(viewdx_path, current_script))
        logger.info(f"Copied running script back to viewdx directory: {os.path.join(viewdx_path, current_script)}")

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        try:
            widgets.error(f"Backup failed: {str(e)}")
            results.usesummary(f"Backup failed: {str(e)}")
        except Exception as notify_error:
            logger.error(f"Failed to notify backup failure: {str(notify_error)}")
            # If backup fails, attempt to restore the original viewdx directory
            if os.path.exists(backup_path):
                if os.path.exists(viewdx_path):
                    shutil.rmtree(viewdx_path)
                    logger.info(f"Removed partially created viewdx directory: {viewdx_path}")
                shutil.move(backup_path, viewdx_path)
                logger.info(f"Restored original viewdx directory from backup: {backup_path}")
            return
        # Clean up temporary script
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
            logger.info(f"Cleaned up temporary script: {temp_script_path}")
        # Clean up temporary modules
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary modules directory: {temp_dir}")
        try:
            root.destory()
            logger.info("Destroyed buffering UI due to backup failure")
        except Exception as tk_error:
            logger.error(f"Failed to distroy buffering UI: {str(tk.error)}")
        sys.exit(1)

    # Step 2: Perform the update and modify deviceinfo
    try:
        # Preserve all fields from the old deviceinfo.py (from the backup)
        old_deviceinfo = {}
        backup_deviceinfo_path = os.path.join(backup_path, "deviceinfo.py")
        if os.path.exists(backup_deviceinfo_path):
            with open(backup_deviceinfo_path, "r") as f:
                exec(f.read(), old_deviceinfo)
            logger.info("Preserved fields from old deviceinfo.py")
        else:
            logger.warning("Old deviceinfo.py not found in backup")

        if source_type.lower() == "pendrive":
            # Use source_path if provided, otherwise try to detect pendrive
            pendrive = get_pendrive()
            if not os.path.exists(pendrive):
                raise ValueError("Pendrive not found!")
            logger.info(f"Using pendrive at: {pendrive}")

            # Look for viewdx.zip in the pendrive
            zip_path = os.path.join(pendrive, "viewdx.zip")
            if not os.path.exists(zip_path):
                raise ValueError("viewdx.zip not found in pendrive!")
            logger.info(f"Found viewdx.zip at: {zip_path}")

            # Extract viewdx.zip to a temporary directory
            os.makedirs(temp_extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            logger.info(f"Extracted viewdx.zip to: {temp_extract_dir}")

            # Copy extracted files to the viewdx directory, skipping protected items and updater.py
            current_script = os.path.basename(__file__)  # e.g., "updater.py"
            temp_extract_dir = os.path.join(temp_extract_dir, "viewdx")
            for item in os.listdir(temp_extract_dir):
                source_item = os.path.join(temp_extract_dir, item)
                dest_item = os.path.join(viewdx_path, item)

                # Skip protected files, folders, and the running updater.py script
                if (item in protected_files or 
                    any(item == folder for folder in protected_folders) or
                    os.path.basename(dest_item) in protected_files or
                    item == current_script):
                    logger.info(f"Skipping protected or running script item: {item}")
                    continue

                if os.path.isdir(source_item):
                    if os.path.exists(dest_item):
                        shutil.rmtree(dest_item)
                        logger.info(f"Removed existing directory: {dest_item}")
                    shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
                    logger.info(f"Copied directory: {source_item} to {dest_item}")
                else:
                    shutil.copy2(source_item, dest_item)
                    logger.info(f"Copied file: {source_item} to {dest_item}")

            # Restore protected files and folders from the backup
            for item in protected_files:
                src_item = os.path.join(backup_path, item)
                dest_item = os.path.join(viewdx_path, item)
                if os.path.exists(src_item):
                    shutil.copy2(src_item, dest_item)
                    logger.info(f"Restored protected file: {item}")
                else:
                    logger.warning(f"Protected file not found in backup: {item}")

            for folder in protected_folders:
                src_folder = os.path.join(backup_path, folder)
                dest_folder = os.path.join(viewdx_path, folder)
                if os.path.exists(src_folder):
                    shutil.copytree(src_folder, dest_folder, dirs_exist_ok=True)
                    logger.info(f"Restored protected folder: {folder}")
                else:
                    logger.warning(f"Protected folder not found in backup: {folder}")

        elif source_type.lower() == "git":
            if not source_path:
                source_path = "https://github.com/your/repository.git"  # Replace with your Git URL
            logger.info(f"Pulling updates from Git repository: {source_path}")
            subprocess.run(["git", "pull", source_path], check=True, cwd=viewdx_path)

            # Restore protected files and folders from the backup after Git pull
            for item in protected_files:
                src_item = os.path.join(backup_path, item)
                dest_item = os.path.join(viewdx_path, item)
                if os.path.exists(src_item):
                    shutil.copy2(src_item, dest_item)
                    logger.info(f"Restored protected file: {item}")
                else:
                    logger.warning(f"Protected file not found in backup: {item}")

            for folder in protected_folders:
                src_folder = os.path.join(backup_path, folder)
                dest_folder = os.path.join(viewdx_path, folder)
                if os.path.exists(src_folder):
                    shutil.copytree(src_folder, dest_folder, dirs_exist_ok=True)
                    logger.info(f"Restored protected folder: {folder}")
                else:
                    logger.warning(f"Protected folder not found in backup: {folder}")

        # Read the new deviceinfo.py to get software_version and comments
        new_deviceinfo = {}
        new_deviceinfo_path = os.path.join(viewdx_path, "deviceinfo.py")
        if not os.path.exists(new_deviceinfo_path):
            raise ValueError("New deviceinfo.py not found after update!")
        logger.info(f"Reading new deviceinfo.py from: {new_deviceinfo_path}")

        with open(new_deviceinfo_path, "r") as f:
            content = f.read()
            exec(content, new_deviceinfo)

        # Extract software_version and comments (the triple-quoted string after software_version)
        new_software_version = new_deviceinfo.get("software_version", "unknown")
        old_dry_chem = old_deviceinfo.get("drychem", [])
        new_dry_chem = new_deviceinfo.get("drychem",old_dry_chem)
        old_qualitative_dict = old_deviceinfo.get("qualitative_dict", {})
        new_qualitative_dict = new_deviceinfo.get("qualitative_dict", old_qualitative_dict)
        

#         comment_match = re.search(r'software_version\s*=\s*".*?"\s*\n\s*\'\'\'(.*?)(\'\'\'|$)', content, re.DOTALL)
#         comment_match = re.search(r'software_version\s*=\s*".*?"\s*\n\s*(?P<quote>["\']{3})(.*?)(?P=quote)', content, re.DOTALL)
#         new_comments = comment_match.group(1).strip() if comment_match else "No comments provided"
#         logger.info(f"New software version: {new_software_version}")
#         logger.info(f"New comments: {new_comments}")

        # Write the updated deviceinfo.py with preserved fields and new values
        with open(os.path.join(viewdx_path, "deviceinfo.py"), "w") as f:
            f.write(f'device_id = "{old_deviceinfo.get("device_id", "")}"\n')
            f.write(f'software_version = "{new_software_version}"\n')
#             f.write(f"'''{new_comments}'''\n")
            f.write(f'install_date = "{old_deviceinfo.get("install_date", "")}"\n')
            f.write(f'lab_name = "{old_deviceinfo.get("lab_name", "")}"\n')
            f.write(f'lab_address = "{old_deviceinfo.get("lab_address", "")}"\n')
            f.write(f'referral = "{old_deviceinfo.get("referral", "")}"\n')
            f.write(f'backup_time = "{old_deviceinfo.get("backup_time", "")}"\n')
            f.write(f'admin_pwd = "{old_deviceinfo.get("admin_pwd", "")}"\n')
            f.write(f'service_pwd = "{old_deviceinfo.get("service_pwd", "")}"\n')
            f.write(f'qcstate = "{old_deviceinfo.get("qcstate", "null")}"\n')
            f.write(f'factorystate = "{old_deviceinfo.get("factorystate", "null")}"\n')
            f.write(f'#qcstates can be "admin", "service" or "null"\n')
            f.write(f'#all small caps\n')
            f.write(f'delstate = "{old_deviceinfo.get("delstate", "enabled")}"\n')
            f.write(f'#delstates can only be "enabled" or "disabled"\n')
            f.write(f'#all small caps\n')
            f.write(f'avail_mem = "{old_deviceinfo.get("avail_mem", "")}"\n')
            f.write(f'hstate = "{old_deviceinfo.get("hstate", "")}"\n')
            f.write(f'wifistate = "{old_deviceinfo.get("wifistate", "")}"\n')
            f.write(f'remoteconnect = "{old_deviceinfo.get("remoteconnect", "")}"\n')
            f.write(f"path = '{viewdx_path}'\n")
            f.write(f'drychem = {old_deviceinfo.get("drychem", [])}' + "\n")
            f.write(f'threelineDict = {old_deviceinfo.get("threelineDict", [])}' + "\n")
            f.write(f'raw_value = "{old_deviceinfo.get("raw_value", "")}"\n')
            f.write(f'peak_threshold = {old_deviceinfo.get("peak_threshold", 5)}\n')
            f.write(f'qualitative_dict = {old_deviceinfo.get("qualitative_dict", {})}' + "\n")
        logger.info("Updated deviceinfo.py with preserved fields")

        # Notify success (with error handling to avoid broken pipe)
        try:
            widgets.notify("Software updated successfully!")
            results.usesummary("Software updated successfully")
            logger.info("Notified user of successful update")
        except Exception as notify_error:
            logger.error(f"Failed to notify success: {str(notify_error)}")

    except Exception as e:
        logger.error(f"Could not update software: {str(e)}")
        try:
            widgets.error(f"Could not update software: {str(e)}")
            results.usesummary(f"Could not update software: {str(e)}")
        except Exception as notify_error:
            logger.error(f"Failed to notify update failure: {str(notify_error)}")
            # Restore the backup from /home/pi/pre_viewdx
            if os.path.exists(backup_path):
                if os.path.exists(viewdx_path):
                    shutil.rmtree(viewdx_path)
                    logger.info(f"Removed failed viewdx directory: {viewdx_path}")
                shutil.move(backup_path, viewdx_path)
                logger.info(f"Restored original viewdx directory from backup: {backup_path}")
        # Clean up temporary script
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
            logger.info(f"Cleaned up temporary script: {temp_script_path}")
        # Clean up temporary modules
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary modules directory: {temp_dir}")
        sys.exit(1)

    finally:
        # Clean up temporary extraction directory and temporary script
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
            logger.info(f"Cleaned up temporary extraction directory: {temp_extract_dir}")
        if os.path.exists(temp_script_path):
            os.remove(temp_script_path)
            logger.info(f"Cleaned up temporary script: {temp_script_path}")
        # Clean up temporary modules
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary modules directory: {temp_dir}")

    # Step 3: Reboot the Raspberry Pi
    try:
        logger.info("Initiating system reboot")
        subprocess.run(["sudo", "reboot"], check=True)
    except BrokenPipeError as bpe:
        # Broken pipe error is expected during reboot as the system shuts down
        logger.info("Broken pipe error during reboot, this is expected as the system is shutting down")
    except Exception as e:
        logger.error(f"Failed to reboot device: {str(e)}")
        # If reboot fails, show a simple Tkinter dialog (or log to console)
        try:

            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showerror("Error", f"Failed to reboot device: {str(e)}\nPlease reboot the device manually.")
            root.destroy()
        except Exception as tk_error:
            logger.error(f"Failed to show reboot error dialog: {str(tk_error)}")
        sys.exit(1)

def get_pendrive():
    result = subprocess.run(["sudo","lsblk", "-o", "NAME,MOUNTPOINT"],stdout = subprocess.PIPE, universal_newlines = True)
    output = result.stdout
    lines = output.split("\n")
    for line in lines[1:]:
        parts = line.split()
        if len(parts)<2:
            continue
        if parts[1].startswith("/") and "media" in parts[1]:
            old_name = parts[1]
            subprocess.run(["sudo", "fatlabel", "/dev/sda1", "VIEWDX"])
            return old_name

if __name__ == "__main__":
    try:
        # Update from pendrive by default
        update(source_type="pendrive", source_path="/media/pi")
    except Exception as e:
        logger.error(f"Update script failed: {str(e)}")
        sys.exit(1)

