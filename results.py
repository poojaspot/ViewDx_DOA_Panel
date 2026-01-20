from fpdf import FPDF
import csv
from tinydb import TinyDB, Query
from datetime import datetime
import widgets
import deviceinfo
import email_proto
import os
import traceback


def usesummary(line: str) -> None:
    try:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        
        log_dir = os.path.join(deviceinfo.path, 'usesummary')
        os.makedirs(log_dir, exist_ok=True)  
        
        filename = f"{deviceinfo.device_id}_usesummary.csv"
        file_path = os.path.join(log_dir, filename)
        
        with open(file_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([time_str, line])
    except Exception as e:
        traceback.print_exc()
        print(f"Error writing to usage summary: {e}")
# usesummary('test')

def report(lines):
    try:
        now = datetime.now()
        date_str = now.strftime("%d_%m_%Y")
        report_dir = os.path.join(deviceinfo.path, 'hardwaretest')
        os.makedirs(report_dir, exist_ok=True)

        filename = f"{deviceinfo.device_id}_hardwaretest.csv"
        report_path = os.path.join(report_dir, filename)

        with open(report_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header rows
            writer.writerow([deviceinfo.lab_name])
            writer.writerow([deviceinfo.lab_address])
            writer.writerow([])
            writer.writerow([f"Report Date: {date_str}"])
            writer.writerow([f"Report Generated for Device id: {deviceinfo.device_id}"])
            writer.writerow([])
            for line in lines:
                writer.writerow([line])
        widgets.error("Hardware scan report generated as CSV")
        email_proto.send_internal_report(filename,"Hardware Test Report")
    except Exception as e:
        widgets.error(f"Error generating report: {e}")
        usesummary(str(e))

def qcreport(lines, analyte):
    try:
        now = datetime.now()
        date_str = now.strftime("%d_%m_%Y")
        report_dir = os.path.join(deviceinfo.path, 'qctest')
        os.makedirs(report_dir, exist_ok=True)

        filename = f"{analyte}_{date_str}.csv"
        report_path = os.path.join(report_dir, filename)

        with open(report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            writer.writerow([deviceinfo.lab_name])
            writer.writerow([deviceinfo.lab_address])
            writer.writerow([])
            writer.writerow([f"Report Date: {date_str}"])
            writer.writerow([f"Device ID: {deviceinfo.device_id}"])
            writer.writerow([])
            for line in lines:
                writer.writerow([line])

            writer.writerow([])
        widgets.error("QC test report has been generated as CSV")
    except Exception as e:
        widgets.error(f"Error generating QC report: {e}")
        usesummary(str(e))

def sanitize_text(text):
    return (text.replace('\u2013', '-')
                .replace('\u2014', '-')
                .replace('\u2018', "'")
                .replace('\u2019', "'")
                .replace('\u201c', '"')
                .replace('\u201d', '"')
                .replace('\u2265', '"'))

class PatientPDF(FPDF):
    def header(self):
        try:
            self.image(deviceinfo.path + 'lab_logo.png', 5, 5, 30)
        except Exception as e:
            print("Logo load error:", e)
#         try:
# #             self.image(deviceinfo.path + 'addl_logo.png', x=175, y=5, w=30)
#         except Exception as e:
#             print("Right logo load error:", e)

        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, txt=sanitize_text(deviceinfo.lab_name), ln=1, align='C')
        self.set_font("helvetica", "", 10)
        self.cell(0, 5, txt=sanitize_text(""), ln=1, align='C')
        self.cell(0, 5, txt=sanitize_text(""), ln=1, align='C')
        self.cell(0, 10, txt=sanitize_text(deviceinfo.lab_address), ln=1, align='C')
        self.ln(5)
        self.set_font("helvetica", "B", 14)
        self.cell(0, 10, txt=sanitize_text("-----------------------------------------SCREENING REPORT-----------------------------------------------------"), ln=1, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "", 8)
        footer_text = sanitize_text(
            "Report Generated on Device id: " + deviceinfo.device_id +
            " Software Version: " + deviceinfo.software_version
        )
        self.cell(0, 10, footer_text, align='L')


def patientpdf(sampleid):
    db = TinyDB(deviceinfo.path + 'results/results.json')
    Sample = Query()
    plist = db.search(Sample.sampleid == sampleid)
    if not plist:
        widgets.error("SampleID could not be fetched")
        return

    pdf = PatientPDF()
    pdf.add_page()

    try:
        index = plist[0]
        pdf.set_font("helvetica", size=12)
        pdf.cell(200, 10, txt=sanitize_text("Sample Id: " + index['sampleid']), ln=1, align='L')
        pdf.cell(200, 10, txt=sanitize_text("Patient Name: " + index['name']), ln=1, align='L')
        pdf.cell(200, 10, txt=sanitize_text("Age: " + index['age']), ln=1, align='L')
        pdf.cell(200, 10, txt=sanitize_text("Gender: " + index['gender']), ln=1, align='L')
        pdf.cell(200, 10, txt=sanitize_text("--------------------------------------------------------------------------------------------------"), ln=1, align='L')

        clinical_csv_path = deviceinfo.path + 'clinicalinterpretation.csv'
        clinical_data = {}
        with open(clinical_csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                clinical_data[row['Analyte'].strip().lower()] = {
                    "Reference Range": row['Reference Range'],
                    "Interpretation": row['Interpretation']
                }

        for l in plist:
            analyte = l['analyte'].strip().lower()
            result = l['result']
            date_str = l['date']
            date = datetime.strptime(date_str, "%d_%m_%Y_%H_%M")
            formatted_date = date.strftime("%d %B %Y, %I:%M %p")

            if pdf.get_y() > 230:
                pdf.add_page()

            text = f"Analyte: {analyte.upper()}  Result: {result}  Date: {formatted_date}"
            pdf.set_font("helvetica", "B", size=11)
            pdf.cell(0, 10, sanitize_text(text), ln=1, align='L')

            try:
                peak_img_path = deviceinfo.path + f'captured/peaks_{sampleid}_{date_str}.png'
                y_before_img = pdf.get_y()
                pdf.image(peak_img_path, x=10, y=y_before_img+5, w=40)
                pdf.ln(45)
            except Exception as e:
                pdf.ln(10)
                print(f"Could not load peak image for {analyte} - {e}")

            if analyte in clinical_data:
                pdf.set_font("helvetica", size=10)
                pdf.multi_cell(0, 7, sanitize_text("Reference Range: " + clinical_data[analyte]["Reference Range"]))
                pdf.multi_cell(0, 7, sanitize_text("Interpretation: " + clinical_data[analyte]["Interpretation"]))

        pdf.cell(0, 10, txt=sanitize_text("--------------------------------------------------------------------------------------------------"), ln=1, align='L')

        pdf.set_font("helvetica", size=8)
        pdf.multi_cell(0, 5, sanitize_text(
            "Disclaimer: This report has been generated using a CDSCO-approved point-of-care medical screening device. "
            "It does not require a signature.\nPlease correlate the findings in this screening report with clinical evaluation for accurate interpretation. "
            "Consult a medical professional as needed."))

        pdf.set_font("helvetica", "B", size=8)
        pdf.cell(0, 10, txt=sanitize_text("-----End of Report----"), ln=1, align='C')

        filename = deviceinfo.path + 'results/' + str(sampleid) + '.pdf'
        pdf.output(filename)

    except Exception as e:
        widgets.error(str(e))
