from datetime import datetime
import json
import deviceinfo
import os
import results
import widgets

# Initialization
try:
    device_id = deviceinfo.device_id 
    software_ver = deviceinfo.software_version 
    install_date = deviceinfo.install_date 
    lab_name = deviceinfo.lab_name  
    lab_address = deviceinfo.lab_address
    referral = deviceinfo.referral
    JSON_FILE = deviceinfo.path + "/results/results.json"
    HL7_FILE = deviceinfo.path + "/results/results.hl7"
except Exception as e:
    widgets.error("Could not initialize hl7 writer")
    results.usesummary(f"Error initializing hl7 writer: {e}")

# Helpers
def load_json_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        widgets.error("Could not find results.json")
        results.usesummary(f"Error loading JSON: {e}")
        return {}

def parse_date(date_str, format_str="%d_%m_%Y_%H_%M"):
    try:
        return datetime.strptime(date_str, format_str).strftime("%Y%m%d%H%M")
    except ValueError:
        return ""

def get_existing_records(hl7_file):
    records = {}
    if os.path.exists(hl7_file):
        try:
            with open(hl7_file, 'r') as f:
                for line in f:
                    if line.startswith("PID"):
                        fields = line.strip().split('|')
                        sample_id = fields[1]
                        name = fields[5] if fields[5] != "UNKNOWN" else ""
                        age = fields[11]
                        gender = fields[8] if fields[8] != "U" else ""
                        records[sample_id] = {"name": name, "age": age, "gender": gender}
        except Exception as e:
            results.usesummary(f"Error reading HL7 file: {e}")
    else:
        try:
            open(hl7_file, 'w').close()
            results.usesummary(f"Created new HL7 file: {hl7_file}")
        except Exception as e:
            results.usesummary(f"Error creating HL7 file: {e}")
    return records

def create_hl7_message(record, set_id):
    now = datetime.now().strftime("%Y%m%d%H%M")
    dt_hl7 = parse_date(record["date"])
    fields = lambda *args: "|".join(args)
    result_str = ",".join(record["result"])
    return "\r".join([
        fields("MSH", "^~\\&", device_id, lab_name, "RECEIVER", "", now, "", "ORU^R01",
               f"MSG{record['sampleid']}{record['date']}", "P", "2.5", "", "", "", software_ver),
        fields("PID", set_id, "", record["sampleid"], "", record.get("name", "UNKNOWN"), "",
               "", record.get("gender", "U"), "", "", record.get("age", ""), "", "", "", "", "", "", "", "", ""),
        fields("PV1", set_id, "O", "", "", "", "", "", referral, ""),
        fields("OBR", set_id, record["sampleid"], record["sampleid"],
               f"{record['analyte']}^{record['analyte']}^LOCAL", "", "", dt_hl7, "", "", "", "", dt_hl7, "", "", "", "", "", device_id, software_ver),
        fields("OBX", set_id, "NM", f"{record['analyte']}^{record['analyte']}^LOCAL", "",
               result_str, record["unit"], "", "", "", "F", "", "", dt_hl7, device_id, "", "", device_id, now),
        fields("NTE", set_id, "CAL_ID", record["cal_id"], "CALIBRATION"),
        fields("EQP", set_id, "IR", device_id, dt_hl7, "", lab_address, "SpotSense", software_ver, device_id),
        f"# JSON Data for ID {set_id}: {json.dumps(record)}"
    ])

def convert_json_to_hl7(json_data):
    messages = {}
    new_ids, updated_ids = [], []
    existing = get_existing_records(HL7_FILE)
    default_data = json_data.get("_default", {})

    for set_id, record in default_data.items():
        messages[set_id] = create_hl7_message(record, set_id)
        if set_id not in existing:
            new_ids.append(set_id)
        else:
            existing_entry = existing[set_id]
            if (record.get("name", "") != existing_entry["name"] or
                record.get("age", "") != existing_entry["age"] or
                record.get("gender", "") != existing_entry["gender"]):
                updated_ids.append(set_id)

    if new_ids:
        results.usesummary(f"Appended new IDs: {', '.join(new_ids)}")
    if updated_ids:
        results.usesummary(f"Updated name, age, gender for IDs: {', '.join(updated_ids)}")

    return messages

def write_hl7():
    json_data = load_json_data(JSON_FILE)
    if not json_data:
        results.usesummary("Failed to convert data due to loading error.")
        return

    hl7_messages = convert_json_to_hl7(json_data)

    if not hl7_messages:
        results.usesummary("No HL7 messages generated from JSON.")
        return

    try:
        with open(HL7_FILE, 'w') as f:
            for msg in hl7_messages.values():
                f.write(msg + "\r\n")
        results.usesummary("HL7 file update complete.")
    except IOError as e:
        results.usesummary(f"Error writing HL7 file: {e}")
