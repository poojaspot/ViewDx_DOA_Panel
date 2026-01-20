import subprocess
from gpiozero import OutputDevice
from gpiozero.exc import GPIOZeroError
from datetime import datetime
import time
import deviceinfo
import results
import utils
import widgets
import re


def log_error(message):
    widgets.error(message)
    results.usesummary(message)

def at_boot(overwrite):
    now = datetime.now()
    today = now.day
    if (deviceinfo.hstate == "Enabled" and today == 10) or overwrite == 1:
        checks = [
            ("Camera check", cameracheck),
            ("Voltage check", undervolt),
            ("RTC check", RTCactive),
            ("SDCard check", speedcheck),
            ("Memory check", Diskmemcheck),
            ("RAM check", Rammemcheck),
        ]
        lines = []

        for label, func in checks:
            try:
                lines.append(f"Running {label}")
                result = func(None)
                lines.append(result)
            except Exception as e:
                log_error(str(e))
                lines.append(f"Could not complete {label.lower()}")

        try:
            results.report(lines)
            widgets.error("Hardware scan completed")
        except Exception as e:
            log_error(str(e))
            widgets.error("Scan completed but could not generate report")

def cameracheck(markup=None):
    try:
        der = subprocess.run('raspistill -o test.jpg', shell=True, check=True)
        print(str(der))
        proc = subprocess.run('vcgencmd get_camera', shell=True, stdout=subprocess.PIPE, text=True)
        output = proc.stdout.strip()
        expected = "supported=1 detected=1"
        status = "Camera detected" if expected in output else "Camera not detected"
        if markup: markup.configure(text=status)
        return status
    except Exception as e:
        log_error(str(e))
        return "Could not check camera status"


def undervolt(markup=None):
    try:
        proc = subprocess.run('vcgencmd get_throttled', shell=True, stdout=subprocess.PIPE, text=True)
        output = proc.stdout.strip()
        status = "Undervoltage detected" if "0x50000" in output else "No Undervoltage detected"
        if markup: markup.configure(text=status)
        return status
    except Exception as e:
        log_error(str(e))
        return "Could not check voltage"


def GPIOcheck(markup):
    outstr = ""
    pin = None  # Define pin here to ensure it's accessible in finally
    try:
        pin1  = OutputDevice(21)
        pin1.on()
        pin2 = OutputDevice(5)
        pin2.on()
        time.sleep(0.1)
        if pin1.is_active:
            outstr = "GPIO 40 pins are functioning"
        elif pin2.is_active:
            outstr = "GPIO 29 pins are functioning"
        else:
            outstr = "GPIO pins may not be functioning"
    except GPIOZeroError:
        outstr = "Error: Could not access GPIO pins."
    except Exception as e:
        outstr = f"An unexpected error occurred: {e}"
    finally:
        if pin:
            pin.close() 
    try:
        markup.configure(text=outstr)
    except Exception:
        pass

    return outstr


def RTCactive(markup=None):
    try:
        start = datetime.now().timestamp()
        time.sleep(5)
        end = datetime.now().timestamp()
        status = "RTC is functioning accurately" if end > start else "RTC is not functioning accurately"
        if markup: markup.configure(text=status)
        return status
    except Exception as e:
        log_error(str(e))
        return "Could not test RTC"


def speedcheck(markup=None):
    try:
        subprocess.run('dd if=/dev/zero of=./speedTestFile bs=20M count=5 oflag=direct', shell=True, check=True)
        subprocess.run('dd if=./speedTestFile of=/dev/zero bs=20M count=5 oflag=dsync', shell=True, check=True)

        subprocess.run("sync; echo 3 > /proc/sys/vm/drop_caches", shell=True)
        output = "Speed test completed"
        if markup: markup.configure(text="Speed test complete (check manually)")
        return output
    except Exception as e:
        log_error(str(e))
        return "Could not complete speed test"


def Diskmemcheck(markup=None):
    try:
        proc = subprocess.run('df -h /', shell=True, stdout=subprocess.PIPE, text=True)
        lines = proc.stdout.strip().split('\n')
        root_line = lines[1] if len(lines) > 1 else ""
        usage_match = re.search(r'\s(\d+)%\s', root_line)
        used_percent = int(usage_match.group(1)) if usage_match else 0
        available = 100 - used_percent

        if markup: markup.configure(text=f"Available: {available}%")
        utils.updatedeviceinfo('avail_mem', deviceinfo.avail_mem, str(available))
        return f"{available}%"
    except Exception as e:
        log_error(str(e))
        return "Could not test memory"


def Rammemcheck(markup=None):
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem_free = next(int(line.split()[1]) for line in lines if "MemAvailable" in line)
        mem_mb = mem_free // 1024
        text = f"Available RAM (Mb) = {mem_mb}"
        if markup: markup.configure(text=text)
        return text
    except Exception as e:
        log_error(str(e))
        return "Could not check RAM"

