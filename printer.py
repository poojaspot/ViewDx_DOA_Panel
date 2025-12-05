import deviceinfo
import widgets

def thermalprint(data_array):
    lab = f"Lab Name: {deviceinfo.lab_name}"
    date = f"Date: {data_array[4]}"
    sample = f"SampleID: {data_array[0]}"
    analyte = f"Analyte: {data_array[1]}"
    result = f"Result: {data_array[3]}"
    device = f"Device: {deviceinfo.device_id}"
    
    try:
        with open('/dev/usb/lp0', 'w') as printer:
            printer.write(f"{lab}\n")
            printer.write(f"{device}\n\n")
            printer.write(f"{sample}\n")
            printer.write(f"{analyte}\n")
            printer.write(f"{result}\n")
            printer.write(f"{date}\n\n")
    except Exception as e:
        widgets.error("Printer is not connected properly.")
        print(f"An error occurred: {e}")

    pass
