import smtplib
from email.message import EmailMessage
import ssl
import os
from datetime import datetime
import subprocess
import time
import deviceinfo
import results
import widgets
import utils
import traceback

def get_smtp_password():
    return deviceinfo.smtp_password

def ping():
    command = ["ping", "-c", "1", "8.8.8.8"]
    resultmsg = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)
    return resultmsg.returncode

def build_email(subject, body, sender_email, receiver_email, pdf_file_path):
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.set_content(body)

    if not os.path.isfile(pdf_file_path):
        widgets.error(f"File not found: {pdf_file_path}")
        raise FileNotFoundError(f"File not found: {pdf_file_path}")
        
    with open(pdf_file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(pdf_file_path)
        )
    return msg

def send_email(PDF_FILE):
    returncode = ping()
    print(returncode)
    if returncode !=0:
        widgets.error("Connect to wifi and try again")
        return
    
    sender_email = "noreply-viewdxresults@spotsense.in"
    receiver_email = deviceinfo.reciever_email
    lab_name = deviceinfo.lab_name
    device_id = deviceinfo.device_id
    subject = f"Your Screening Report is Ready | {lab_name}"

    password = get_smtp_password()

    body = (
        "Dear Sir/Madam,\n\n"
        "Greetings!\n\n"
        "Your screening report is now available. Please find the attached report for your reference.\n\n"
        "If you have any questions or need assistance, our team is happy to help.\n")
#         "You can reach us through:\n"
#         "Mobile: 000000000\n"
#         "WhatsApp: 0000000000\n\n"
#         f"Device ID: {device_id}\n\n"
#         f"Thank you!\nBest Regards,\n{lab_name}\n"
#     )

    try:
        msg = build_email(subject, body, sender_email, receiver_email, PDF_FILE)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)
        widgets.error("Email sent successfully!")
    except Exception as e:
        widgets.error(f"Failed to send email:\n{str(e)}")

def send_results():
    returncode = ping()
    print(returncode)
    if returncode !=0:
        widgets.error("Connect to wifi and try again")
        return
    sender_email = "noreply-viewdxresults@spotsense.in"
    receiver_email = deviceinfo.reciever_email
    lab_name = deviceinfo.lab_name
    device_id = deviceinfo.device_id
    json_path = deviceinfo.path+"results/results.json"
    subject = f"Result Database | {device_id}"

    password = get_smtp_password()

    body = (
        "Dear Sir/Madam,\n\n"
        "Please find the attached result database for your reference.\n\n"
        "If you have any questions or need assistance, our team is happy to help.\n"
        f"Device ID: {device_id}\n\n"
        f"Thank you!\nBest Regards,\n{lab_name}\nTelerad Foundation"
    )
    try:
        csv_path = utils.json_to_csv(json_path)
        if not csv_path:
            results.usesummary("CSV file not generated. Email not sent.")
            widgets.error("CSV file not generated. Email not sent.")
            return
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg.set_content(body)

        with open(csv_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(csv_path)
            msg.add_attachment(file_data, maintype='application', subtype='octet-stream', filename=file_name)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, password)
            server.send_message(msg)

        widgets.error("Email sent successfully!")
        os.remove(csv_path)
        results.usesummary(f"{csv_path} deleted after sending.")
    except Exception as e:
        traceback.print_exc()
        print(e)
        results.usesummary(f"Failed to send results database email:\n{str(e)}")
        widgets.error("Failed to send results database email")

def send_internal_report(CSV_FILE, report_type="Hardware/Use Summary Report"):
    returncode = ping()
    print(returncode)
    if returncode !=0:
        widgets.error("Connect to wifi and try again")
    else:
        
        sender_email = "noreply-viewdxresults@spotsense.in"
        receiver_email = "customer_care@spotsense.in"
        password = get_smtp_password()
        lab_name = deviceinfo.lab_name
        device_id = deviceinfo.device_id
        subject = f"{report_type} | {lab_name} | Device ID: {device_id}"

        body = (
            f"Dear Customer Care,\n\n"
            f"Please find attached the automated {report_type.lower()} from {lab_name}.\n\n"
            f"Device ID: {device_id}\n"
            "This email was generated and sent automatically by the system.\n\n"
            "Best,\nAutomated System"
        )

        try:
            msg = EmailMessage()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = subject
            msg.set_content(body)
            if not os.path.isfile(CSV_FILE):
                widgets.error(f"File not found: {CSV_FILE}")
                raise FileNotFoundError(f"File not found: {CSV_FILE}")

            with open(CSV_FILE, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="text",
                    subtype="csv",
                    filename=os.path.basename(CSV_FILE)
                )
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, password)
                server.send_message(msg)
                print("Email sent successfully")
                widgets.error("Report sent successfully.")
        except Exception as e:
            print(e)
            widgets.error("Verify wifi and email address and try again.")
            results.usesummary(e)



