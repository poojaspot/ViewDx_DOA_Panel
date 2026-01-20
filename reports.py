# -*- coding: utf-8 -*-
"""
Created on Sat Feb 11 14:06:29 2023

@author: amrit
"""
from fpdf import FPDF
from time import sleep
from datetime import datetime, date
import deviceinfo
import widgets
import imagepro
import widgets
from fpdf import FPDF
import csv
import deviceinfo
from tinydb import TinyDB, Query, where
from tinydb.operations import add, delete, set, subtract
from tinydb.table import Document
import subprocess
from datetime import datetime
from PIL import Image
import widgets
import traceback

def usesummary(line):
    now = datetime.now()
    date = now.strftime("%d_%m_%Y")
    time = now.strftime("%H:%M:%S")
    f = open(deviceinfo.path+'usesummary/usesummary_'+str(deviceinfo.device_id)+'_'+str(date)+'.csv', 'a')
    writer = csv.writer(f)
    row = str(time)+':'+line+"\n"
    print(row)
    f.write(row)
    f.close()
    
def qcreport(lines, analyte):
    try:
        if (lines==""):widgets.error("QC Test data not available")
        else:
            now = datetime.now()
            date = now.strftime("%d_%m_%Y")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", size = 14)
            try:
                pdf.image(deviceinfo.path +'lab_logo.png',5,5,20)
                pdf.cell(200, 10, txt = deviceinfo.lab_name, ln=1,align='C')
                pdf.cell(200, 10, txt = deviceinfo.lab_address, ln=1,align='C')
                pdf.cell(200, 10, txt = "---------------------------------------------------REPORT-----------------------------------------------------", ln=3,align='C')
            except: print('no lab logo')

            pdf.cell(200, 10, txt = "Report Date: "+str(date), ln=1,align='L')
            pdf.cell(200, 10, txt = "Report Generated for Device id: "+deviceinfo.device_id,ln=2,align='L')   
            i = 1                 
            for l in lines:
                pdf.cell(200, 10, txt = l, ln=3+i,align='L')
                i = i+1
            pdf.output(deviceinfo.path+'qctest/'+analyte+'_'+str(date)+'.pdf')
            widgets.error("QC test report has been generated")
    except Exception as e: widgets.error(e)
    pass



def genpdf(sampleid):
    db = TinyDB(deviceinfo.path+'/results/results.json')
    Sample = Query()
    
    list = db.search(Sample.sample_id == str(sampleid))
    if (list==""): widgets.error("SampleID could not be fetched")
    print(list)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size = 14)
    try:
        pdf.image(deviceinfo.path +'lab_logo.png',5,5,20)
    except Exception as e:
        print(e)
        print('no lab logo genpdf')
    try:
        pdf.cell(200, 10, txt = deviceinfo.lab_name, ln=1,align='C')
        pdf.cell(200, 10, txt = deviceinfo.lab_address, ln=1,align='C')
        pdf.cell(200, 10, txt = "---------------------------------------------------REPORT-----------------------------------------------------", ln=3,align='C')
    except Exception as e: print(e)

    for l in list:
        pdf.cell(200, 10, txt = "Tube Id: "+l['sample_id'], ln=1,align='L')
        pdf.cell(200, 10, txt = "Bottle Type: "+l['tube_type'], ln=2,align='L')
        pdf.cell(200, 10, txt = "Sample Collection Date: "+l['col_date'], ln=3,align='L')
        pdf.cell(200, 10, txt = "--------------------------------------------------------------------------------------------------", ln=4,align='L')
        pdf.cell(200, 10, txt = "Sample Id: "+l['patient_id'], ln=6,align='L')
        try:pdf.cell(200, 10, txt = "Patient Name: "+l['name'], ln=7,align='L')
        except: ''
        try:pdf.cell(200, 10, txt = "Age: "+l['age'], ln=8,align='L')
        except:''
        try:pdf.cell(200, 10, txt = "Gender: "+l['gender'], ln=9,align='L')
        except:''
        try:pdf.cell(200, 10, txt = "Referred by: "+l['refer'], ln=10,align='L')
        except:''
        pdf.cell(200, 10, txt = "Result: "+l['readings']['result'], ln=11,align='L')
        pdf.cell(200, 10, txt = "Time of test: "+l['readings']['test_time'], ln=12,align='L')
        pdf.cell(200, 10, txt = "--------------------------------------------------------------------------------------------------", ln=13,align='L')
        pdf.cell(200, 10, txt = "", ln=14,align='L')
        pdf.cell(200, 10, txt = "", ln=15,align='L')
        pdf.cell(200, 10, txt = "", ln=16,align='L')
        pdf.cell(200, 10, txt = "Signature: ", ln=16,align='L')
        pdf.set_font("helvetica", size = 6)
        pdf.cell(200, 10, txt = "Report Generated on Device id: MXCC_proto; Software version 0.1 ",ln=17,align='L')
                
    pdf.output(deviceinfo.path+'results/'+str(sampleid)+'.pdf')

def htest(lines):
    try:
        if (lines==""):widgets.error("Hardware scan data not available")
        else:
            now = datetime.now()
            date = now.strftime("%d_%m_%Y")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", size = 12)
            pdf.cell(200, 10, txt = "Report Date: "+str(date), ln=1,align='L')
            pdf.cell(200, 10, txt = "Report Generated for Device id: "+deviceinfo.device_id,ln=2,align='L')   
            i = 1                 
            for l in lines:
                pdf.cell(200, 10, txt = l, ln=3+i,align='L')
                i = i+1
            pdf.output(deviceinfo.path+'hardwaretest/'+str(date)+'.pdf')
            widgets.error("Hardware scan report generated")
    except Exception as e: widgets.error(e)
    pass