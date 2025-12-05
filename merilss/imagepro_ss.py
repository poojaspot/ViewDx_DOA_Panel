from picamera2 import Picamera2, Preview
from libcamera import Transform 
from gpiozero import LED
from PIL import Image
import time
import matplotlib.pyplot as plt
import numpy as np
import cv2
from tinydb import TinyDB, Query

from scipy.signal import find_peaks, peak_prominences, savgol_filter
from scipy import sparse
from scipy.sparse.linalg import spsolve
from pyzbar.pyzbar import decode
import os

import widgets
import deviceinfo
import results
import utils
import traceback



def camcapture(sampleid, date, gpio_pin_board):
    # Mapping from BOARD to BCM numbering for the specified pins
    BOARD_TO_BCM = {40: 21, 29: 5}
    if gpio_pin_board not in BOARD_TO_BCM:
        raise ValueError(f"Unsupported BOARD pin: {gpio_pin_board}. Use 29 or 40.")
    bcm_pin = BOARD_TO_BCM[gpio_pin_board]

    image_folder = 'captured'
    
    # Initialize hardware objects
    picam2 = Picamera2()
    light = LED(bcm_pin)

    # Construct the image path
    image_path = os.path.join(deviceinfo.path, image_folder)
    os.makedirs(image_path, exist_ok=True)
    image_filename = f'capturedimage_pil_{sampleid}_{date}.jpg'
    full_path = os.path.join(image_path, image_filename)

    try:
        results.usesummary("Starting camera capture...")
        light.on() #Turn on LED and
        
        # Configure the camera for a still capture
        config = picam2.create_preview_configuration(main={"size":(3280,2464)},lores={"size":(3280,2464)})
        picam2.configure(config)
#         "AnalogueGain": 0.5, "FrameDurationLimits": (33333,1200000)
#         controls = {
#             
#             "AwbEnable": True,     
#             "ExposureValue": int(1*10**6)
#         }
#         picam2.set_controls(controls)

        #  start the camera to apply settings
      
        picam2.start_preview(Preview.QT)
        picam2.start()
        time.sleep(2)
        picam2.capture_file(full_path)
        
        results.usesummary(f"Image saved to: {full_path}")

    except Exception as e:
        traceback.print_exc()
        results.usesummary(f"Error during camera operation: {e}")  

    finally:
        if picam2.started:
            picam2.stop()
        picam2.close()
        light.close()

    image_pil = Image.open(full_path)
    image_rs = image_pil.resize((800,480),Image.Resampling.LANCZOS)
    numpy_img = np.array(image_rs)
    image_cv2 = cv2.cvtColor(numpy_img,cv2.COLOR_RGB2BGR)
    image_filename = f'capturedimage_{sampleid}_{date}.jpg'
    full_path = os.path.join(image_path, image_filename)
    cv2.imwrite(full_path,image_cv2)
    input_image = cv2.imread(full_path)
    if input_image is None:
        results.usesummary(f"Image not found or unreadable at: {full_path}")
        raise FileNotFoundError(f"Image not found or unreadable: {full_path}")
        
    return input_image
#------------------------------------picam--------------------------------------------------------------
# def camcapture(sampleid, date, gpio_no):
#     preview_time=3
#     image_folder='captured'
#     camera = PiCamera()
#     image_path = os.path.join(deviceinfo.path, image_folder)
#     os.makedirs(image_path, exist_ok=True)
#     image_filename = f'capturedimage_{sampleid}_{date}.jpg'
#     full_path = os.path.join(image_path, image_filename)
# 
#     GPIO.setwarnings(False)
#     GPIO.setmode(GPIO.BOARD)
#     GPIO.setup(gpio_no, GPIO.OUT)
# 
#     try:
#         results.usesummary("Starting camera capture...")
#         GPIO.output(gpio_no, True)
#         camera.start_preview()
#         time.sleep(preview_time)
#         camera.capture(full_path)
#         camera.stop_preview()
#         GPIO.output(gpio_no, False)
#         results.usesummary(f"Image saved to: {full_path}")
#     except Exception as e:
#         results.usesummary(f"Error during camera operation: {e}")
#         raise
#     finally:
#         camera.close()
#         GPIO.cleanup()
# 
#     input_image = cv2.imread(full_path)
#     if input_image is None:
#         results.usesummary(f"Image not found or unreadable at: {full_path}")
#         raise FileNotFoundError(f"Image not found or unreadable: {full_path}")    
#     return input_image
#--------------------------------------------------------------------------------------------------------------------

#need to add logic to identify ideal blur parameters
#need to check where this function fails
 
def find_lfa(image, sampleid, date):
    if image is None:
        results.usesummary("Invalid image input: image is None")
        raise ValueError("Invalid image input")

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        kernel = np.ones((5, 5), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        contour_img = image.copy()
        cv2.drawContours(contour_img, contours,-1,(0,255,0),2)
        save_dir = os.path.join(deviceinfo.path, 'captured')
        save_path = os.path.join(save_dir, f'contour_{sampleid}_{date}.jpg')
        cv2.imwrite(save_path, contour_img)
        if not contours:
            results.usesummary("No contours found in image.")
            return None

        cassette_contour = max(contours, key=cv2.contourArea, default=None)

        if cassette_contour is None:
            results.usesummary("No valid cassette contour detected.")
            return None

        perimeter = cv2.arcLength(cassette_contour, True)
        print(perimeter)
        if not (1000 <= perimeter <= 3000):
            results.usesummary(f"Cassette contour perimeter {perimeter} not in expected range (1000–2000).")
            return None

        x, y, w, h = cv2.boundingRect(cassette_contour)
        aspect_ratio = round(float(w) / h, 2)
        if not (0.6 <= aspect_ratio <= 0.85):
            results.usesummary(f"Aspect ratio {aspect_ratio} not in expected range (0.6–0.85).")
            return None

        roi = image[y:y + h, x:x + w]

        save_dir = os.path.join(deviceinfo.path, 'captured')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f'test_cassette_{sampleid}_{date}.jpg')
        cv2.imwrite(save_path, roi)
        results.usesummary(f"ROI successfully saved: {save_path}")

        return roi

    except Exception as e:
        widgets.error(str(e))
        results.usesummary(f"Error in find_lfa: {str(e)}")
        return None

def find_testwindow(img, sampleid, date):
    roi_image = None
    image = img.copy()
    
    # Preprocess image: blur and grayscale
    blurred = cv2.GaussianBlur(image, (15, 15), 0)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    
    # Sobel edge detection (x and y gradients)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    
    abs_grad_x = cv2.convertScaleAbs(sobelx)
    abs_grad_y = cv2.convertScaleAbs(sobely)
    # Weighted sum of gradients to emphasize edges
    grad = cv2.addWeighted(abs_grad_x, 0.05, abs_grad_y, 0.05, 0) 
    
    # Threshold using Otsu's method to binarize edges
    ret, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = thresh.astype(np.uint8)
    
    # Find contours on thresholded image
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    
    rect_candidates = []
    
    img_height, img_width = gray.shape
    
    for contour in contours:
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        if len(approx) >= 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = w / float(h) if h != 0 else 0
            perimeter = cv2.arcLength(contour, True)
            
            # Filter contours by aspect ratio and size
            # Can aspect ratio, perimeter and w be identified dynamically
            print(aspect_ratio,perimeter, w)
            if 0.21 <= aspect_ratio <= 0.95 and 500 <= perimeter < 2000:
                
                # Prefer smaller width contours, but if none, take all
                # Check where this logic fails
                if w <= 120 or not rect_candidates:
                    print(aspect_ratio,perimeter,"selected", h,w)
                    cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 2)
                    cv2.imwrite(deviceinfo.path + f'captured/rect{sampleid}_{date}.jpg', image)
                    area = h * w
                    rect_candidates.append((x, y, w, h, area, contour))
    
    try:
        
        if rect_candidates:
            for rect in rect_candidates:
            # Sort by area descending to pick largest candidate
#             rect_candidates.sort(key=lambda r: r[4], reverse=True)
                x1, y1, w1, h1, area, best_contour = rect
            # can h1 be identifiedd dynamically rather than a fixed value
                roi_img = img.copy()
                print(h)
#             roi_image = roi_img[y1:y1 + h1, x1:x1 + w1]
#             cv2.imwrite(deviceinfo.path + f'captured/roi_{sampleid}_{date}.jpg', roi_image)
                if 200 <= h1 < 300:
                    
                    roi_image = roi_img[y1:y1 + h1, x1:x1 + w1]
                    cv2.imwrite(deviceinfo.path + f'captured/roi_{sampleid}_{date}.jpg', roi_image)
                else:
                    widgets.error("Test card is not inserted properly")
    #                 roi_image = roi_img[y1:y1 + h1, x1:x1 + w1]
#                 cv2.imwrite(deviceinfo.path + f'captured/roi_{sampleid}_{date}.jpg', roi_image)
        else:
            widgets.error("Test window is not detected, Please re-insert the test can try again.")
    except Exception as e:
        widgets.error(f"Error processing test window: {e}")
    
    return roi_image

def roi_segment(captured_image, sampleid, date):
    roi_seg = None
    try:
        test_cassette = find_lfa(captured_image, sampleid, date)
        if test_cassette is not None:
            roi_seg = find_testwindow(test_cassette, sampleid, date)
        else:
            widgets.error("Test cassette not detected.")
    except Exception as e:
        widgets.error(f"Error in ROI segmentation: {e}")
        results.usesummary(f"Error in roi_segment: {e}")
    return roi_seg


def get_prominences(result_array, sampleid, date):
    try:
        # Preprocess and baseline correction
        filtered_data = filter_result_array(result_array)
        print('len',len(filtered_data), len(result_array))
        inverted_data = 0 - filtered_data  # invert signal
        baseline = baseline_correction(inverted_data, 1000, 0.005)
        corrected_data = inverted_data - baseline
        
        # Detect noise peaks and calculate prominences
        noise_peaks, _ = find_peaks(corrected_data[5:])
        noise_prominences = peak_prominences(corrected_data, noise_peaks)[0]

        len_noise = None
        if len(noise_prominences) < 100:
            noise_range = max(noise_prominences) - min(noise_prominences)
            len_noise = 51 if noise_range < 20 else len(noise_prominences)

        pr_val = int(deviceinfo.peak_threshold)
        peaks, _ = find_peaks(corrected_data, prominence=pr_val, width=(5, 50))
        prominences = peak_prominences(corrected_data, peaks)[0]
        print(prominences)

        results.usesummary(f"Detected prominences: {prominences}")

        # Plot and save peak detection result
        plt.plot(corrected_data, label='Baseline corrected data')
        plt.plot(peaks, corrected_data[peaks], 'x', label='Detected peaks')
        plt.legend()
        plt.savefig(f"{deviceinfo.path}captured/peaks_{sampleid}_{date}.png")
        plt.close()

        return peaks, prominences

    except Exception as e:
        results.usesummary(f"Error in get_prominences: {e}")
        widgets.error(f"Error in prominence detection: {e}")
        return None, None
        
def baseline_correction(y, lam, p):
    L = len(y)
    D = sparse.diags([1,-2,1],[0,-1,-2],shape=(L,L-2))
    D = lam*D.dot(D.transpose())
    w = np.ones(L)
    W = sparse.spdiags(w,0,L,L)
    for i in range(1,10):
        W.setdiag(w)
        Z = W+D
        z = spsolve(Z, w*y)
        w = p*(y>z)+(1-p)*(y<z)
    return z

def scan_card(segment):
    height, width = segment.shape[:2]
    result_array = []

    for y in range(height):
        line = segment[y:y+3, 0:width]
        avg_color_per_row = np.average(line, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        sum_rgb = np.sum(avg_color)
        result_array.append(sum_rgb)

    results.usesummary(f"scan_card processed {height} lines, width {width}")
    return np.array(result_array)


def filter_result_array(result_array, window=35):
    data = np.array(result_array)
    differences = np.abs(np.ediff1d(data))

    if len(differences) < window:
        results.usesummary("filter_result_array: Not enough data to filter meaningfully.")
        return data

    max_diff_index = np.argmax(differences[:window])
    results.usesummary(f"filter_result_array: Max difference at index {max_diff_index}")

    start_index = max_diff_index + 30
    end_index = -50 if len(data) > 50 else len(data)
    return data[start_index:end_index]

def rgb2cmk(img):
    bgr_norm = img.astype(np.float64) / 255.0
    K = 1 - np.max(bgr_norm, axis=2)
    denom = 1 - K
    denom[denom == 0] = 1
    C = (1 - bgr_norm[..., 2] - K) / denom
    M = (1 - bgr_norm[..., 1] - K) / denom
    Y = (1 - bgr_norm[..., 0] - K) / denom
    CMY = (np.dstack((C, M, Y)) * 255).astype(np.uint8)
    results.usesummary("rgb2cmk: Converted RGB image to CMY color space")
    return CMY

def check_bg(test_window, sampleid, date):
    flag = 0  # default no high background
    if test_window is None:
        err_msg = "Test card is not inserted properly."
        widgets.error(err_msg)
        results.usesummary(err_msg)
        return flag

    try:
        img_cmy = rgb2cmk(test_window)
        _, m, _ = cv2.split(img_cmy)

        hist = cv2.calcHist([m], [0], None, [256], [0, 256])
        hist_smooth = savgol_filter(hist[:, 0], 21, 2)

        #if already hist is being plotted do we need to add peaks logic to identify background
        peaks, _ = find_peaks(hist_smooth, distance=20, prominence=80, width=(5, 50))
        prominences = peak_prominences(hist_smooth, peaks)[0]

        if len(prominences) > 1:
            flag = 1
            results.usesummary(f"{sampleid} has high background.")
        else:
            results.usesummary(f"{sampleid} doesn't have high background.")
        print('check_bg',flag)

    except Exception as e:
        err_msg = f"Error occurred while reading background: {e}"
        results.usesummary(err_msg)
        widgets.error(err_msg)
        
    return flag


def val_card(result_array, peaks, prominences, bg_flag, analyte, sampleid, date):
    pr_val = int(deviceinfo.peak_threshold)
    test_value = control_value = ref_value = value = None
    is_threeline = analyte.strip().lower() in [x.lower() for x in deviceinfo.threelineDict]
    print('val_Card',len(prominences),prominences)
    try:
        if len(prominences) == 0: value = "Err 02: no control line detected"
        elif len(prominences) == 1: value = "Below detection limit"
        elif len(prominences) == 2:
            if is_threeline is False:
                control_value = round(prominences[0], 3)
                test_value = round(prominences[1], 3)
            else:
                print('prom =2 ',"threeline")
#                 test_value = None
                ref_value = round(prominences[1], 3)
                control_value = round(prominences[0], 3)
                value = "Below detection limit"
        elif len(prominences) == 3 and is_threeline:
            print("prom=3","threeline")
            control_value = round(prominences[0], 3)
            ref_value = round(prominences[1], 3)
            test_value = round(prominences[2], 3)
            print("control_value,ref_value,test_value",control_value,ref_value,test_value)
        else:
            print('bg',bg_flag)
            if bg_flag == 1:
                widgets.error("Err 03: Test has high background.")
            elif bg_flag == 0:
                if all(x >pr_val for x in prominences):
                    value = "Err 03: Test has high background."
                    widgets.error("Err 03: Test has high background.")
                else:
                    pr_val += 2
                    peaks, prominences = get_prominences(result_array, sampleid, date)
                    
                    if len(prominences) == 0: value = "Err 02: no control line detected"
                    elif len(prominences) == 1: value = "Below detection limit"
                    elif len(prominences) == 2:
                        if is_threeline is False:
                            test_value = round(prominences[1], 3)
                            control_value = round(prominences[0], 3)
                        else:
                            print("threeline")
                            value = "Below detection limit"
#                             test_value = 0
                            ref_value = round(prominences[1], 3)
                            control_value = round(prominences[0], 3)
                            
                    elif len(prominences) == 3 and is_threeline:
                        print("threeline")
                        print('376',prominences)
                        control_value = round(prominences[0], 3)
                        ref_value = round(prominences[1], 3)
                        test_value = round(prominences[2], 3)       
        try:
            print('try',value)
            if value is None:
                if deviceinfo.raw_value == 'test':
                    value = test_value
                elif deviceinfo.raw_value == 'ratio':
                    if control_value is not None and control_value != 0 and test_value is not None:
                        value = round(test_value / control_value, 3)
                        print('380',value)
                    elif control_value is None:
                        value = "Err 02: no control line detected"
                else:
                    results.usesummary("deviceinfo.raw_value is not defined correctly.")
        except Exception as e:
            results.usesummary(f"Value calculation error: {str(e)}")
        print('final_value', value)
    except Exception as e:
        print(e)
        results.usesummary(f"Error in val_card: {str(e)}")
        value = "Err 05: Could not read test"
    
    summary_string = (
        f"Prominences read for {sampleid} for {analyte}: "
        f"Test line intensity: {test_value} "
        f"Control line: {control_value} "
        f"Ref line: {ref_value} "
        f"Raw Value: {value}"
    )
    results.usesummary(summary_string)   
    return test_value, control_value, value

def cal_conc(temp, cal_id):
    print('calid temp',temp)
    if not isinstance(temp,(int,float,str)):
        raise ValueError("Invalid test value")
    if not isinstance(cal_id,str):
        raise ValueError("Invalid calibiration ID")
    if 'Err' in str(temp):
        result = temp
        return result
    if 'Below' in str(temp):
        result = temp
        return result
    try:
        temp_str = str(temp)
        y = float(temp)
    except Exception as e:
        results.usesummary(f"Error converting temp to float: {e}")
        traceback.print_exc()
        return "Err 06: invalid test value"
    if cal_id == '1/1/1/1' or 'Err' in temp_str or 'Below' in temp_str:
        return temp_str

    if ":" in cal_id:
        parts = cal_id.split(":")
        try:
            cutoff = float(parts[1])
            cal_id = parts[0] if y <= cutoff else parts[2]
        except Exception as e:
            results.usesummary(f"Error parsing cutoff in cal_id: {e}")
            return "Err 07: invalid cutoff in cal_id"

    try:
        details = [float(x)/100 if i != 0 else float(x) for i, x in enumerate(cal_id.split("/"))]

        if len(details) < 3:
            raise ValueError("Calibration ID must have at least 3 parts")

        model_type = int(details[0])
        result = None

        # Model type 1: Linear (y = bx + c → x = (y - c)/b)
        if model_type == 1:
            b, c = details[1:3]
            res = (y - c) / b

        # Model type 2: Log-linear (y = b * ln(x) + c → x = exp((y - c)/b))
        elif model_type == 2:
            b, c = details[1:3]
            res = np.exp((y - c) / b)

        # Model type 3: Power curve (y = b * x^c → x = 10^((log(y/b))/c))
        elif model_type == 3:
            b, c = details[1:3]
            res = pow(10, (np.log(y / b) / c))

        # Model type 4+: 4PL regression
        elif len(details) >= 5:
            a, b, c, d = details[1:5]
            try:
                h = ((a - d) / (y - d)) - 1
                if h <= 0:
                    return "Below detectable limits"
                res = c * pow(h, 1 / b)
            except Exception as e:
                results.usesummary(f"4PL calculation error: {e}")
                return "Err 08: 4PL computation failed"
        else:
            return "Err 09: Unknown calibration model"

        # Post-processing of result
        if isinstance(res, complex):
            result = "Outside measuring range"
        elif res <= 0:
            result = "Below detectable limits"
        else:
            result = str(round(res, 2))

        results.usesummary(
            f"Calibration ID: {cal_id}, Measured: {y}, Calculated: {result}"
        )
        return result

    except Exception as e:
        results.usesummary(f"Error in cal_conc: {str(e)}")
        return "Err 10: Calibration failed"

def val_qualitative(peaks, prominences, bg_flag, analyte, sampleid, date, ordered_marker_array):
    m_array = ordered_marker_array
    value = "Unknown error"

    try:
        if bg_flag == 1:
            value = "Err 03: Test has high background."
        elif not prominences or len(prominences) == 0:
            value = "Err 02: No control line."
        else:
            num_lines = len(prominences)
            num_markers = len(m_array)

            if num_markers == 1:
                value = f"Positive for {m_array[0]}" if num_lines == 2 else f"Negative for {m_array[0]}"
            elif num_markers == 2:
                if num_lines == 3:
                    value = f"Positive for {m_array[0]} and {m_array[1]}"
                elif num_lines == 2:
                    if (peaks[1] - peaks[0]) < 100:
                        value = f"Positive for {m_array[0]}"
                    else:
                        value = f"Positive for {m_array[1]}"
                else:
                    value = f"Negative for {m_array[0]} and {m_array[1]}"
    except Exception as e:
        value = "Err 11: Exception in qualitative analysis"
        results.usesummary(f"Exception occurred in val_qualitative: {e}")
    results.usesummary(f"Qualitative result for [{analyte}] is [{value}]")
    return value


def val_bloodgroup(prominences, peaks, bg_flag):
    value = "Unknown"
    
    if not prominences or not peaks:
        raise ValueError("Invalid input parameters: prominences or peaks are missing")
    
    try:
        if len(prominences) == 0:
            value = "O -ve"
        elif len(prominences) == 3:
            value = "AB +ve"
        elif len(prominences) > 3 and bg_flag == 1:
            value = "Err 03: Test has high background"
        else:
            res_dict = []
            for peak in peaks:
                if 0 < peak < 70:
                    res_dict.append("D")
                elif 70 < peak < 130:
                    res_dict.append("B")
                elif 130 < peak < 200:
                    res_dict.append("A")

            if "D" in res_dict:
                if "A" in res_dict and "B" not in res_dict:
                    value = "A +ve"
                elif "B" in res_dict and "A" not in res_dict:
                    value = "B +ve"
                elif "A" in res_dict and "B" in res_dict:
                    value = "AB +ve"
                elif "A" not in res_dict and "B" not in res_dict:
                    value = "O +ve"
            else:
                if "A" in res_dict and "B" not in res_dict:
                    value = "A -ve"
                elif "B" in res_dict and "A" not in res_dict:
                    value = "B -ve"
                elif "A" in res_dict and "B" in res_dict:
                    value = "AB -ve"

    except Exception as e:
        widgets.error("Error occurred while reading the test.")
        results.usesummary(f"Error in val_bloodgroup: {e}")
        value = "Err 12: Exception in blood group test"

    return value

# ---------------------------------------------------------------------
def read_test(data_array, overwrite):
    from tinydb import TinyDB, Query
    import traceback

    sample_id = data_array[0]
    analyte = data_array[1].lower()
    cal_id = data_array[2]
    date = data_array[4]
    unit = data_array[9]
    val = ''

    # Overwrite last test if flag is set
    if overwrite == 1:
        try:
            db = TinyDB(deviceinfo.path + "results/results.json")
            last = db.all()[-1]
            db.remove(doc_ids=[last.doc_id])
            results.usesummary("Test result was overwritten.")
        except Exception:
            results.usesummary("No results overwritten.")

    # Capture image
    captured_image = camcapture(sample_id, date, 40)
    results.usesummary("Image Captured.")

    try:
        # ROI and background setup
        roi_seg = roi_segment(captured_image, sample_id, date)
        bg_flag = check_bg(roi_seg, sample_id, date)
        result_array = scan_card(roi_seg)
        peaks, prominences = get_prominences(result_array, sample_id, date)

        # Handle qualitative tests
        if analyte in (key.lower() for key in deviceinfo.qualitative_dict.keys()):
            ordered_marker_array = deviceinfo.qualitative_dict[data_array[1]]
            val = val_qualitative(peaks, prominences, bg_flag, analyte, sample_id, date, ordered_marker_array)

        # Handle blood group tests
        elif analyte == "Blood group":
            val = val_bloodgroup(prominences, peaks, bg_flag)

        # Handle quantitative tests
        else:
            tv, cv, value = val_card(result_array, peaks, prominences, bg_flag, analyte, sample_id, date)
            print(tv,cv,value)
            val = cal_conc(value, cal_id)
            results.usesummary(f"Calculated value is: {val}")

            try:
                analytedb = TinyDB(deviceinfo.path + 'analytes.json')
                sample_query = Query()
                analyte_entry = analytedb.search(sample_query.analyte == data_array[1])
                a = analyte_entry[0]

                try:
                    val_num = float(val)
                    measl = float(a['measl'])
                    measu = float(a['measu'])

                    if val_num < measl:
                        val = f"Below {measl} {a['unit']}"
                    elif val_num > measu:
                        val = f"Above {measu} {a['unit']}"
                    else:
                        val = f"{val} {unit}"
                except ValueError:
                    if "Below" in val:
                        val = f"Below {a['measl']} {a['unit']}"
                    elif "Err" in val:
                        
                        val = f"{val}"
                        results.usesummary(f"Error occured while reading test. Error is: {val}")
                        widgets.error(val)
            except:
                pass

    except Exception as e:
        traceback.print_exc()
        widgets.error("Error occurred while reading the test.")
        results.usesummary(e)

    try:
        data_array[3] = val
#         if "Err" in val:
#            val = "Error occurred while reading the test."
        db = TinyDB(deviceinfo.path + "results/results.json")
        result = {
            "sampleid": sample_id,
            "analyte": data_array[1],
            "cal_id": cal_id,
            "result": val,
            "unit": unit,
            "date": date,
            "name": data_array[5],
            "age": data_array[6],
            "gender": data_array[7]
        }
        db.insert(result)
        results.usesummary(f"Result for {sample_id} added in database.")
        results.usesummary(f"Result is {result}")
    except Exception:
        traceback.print_exc()
        widgets.error("Could not add result to database.")
#--------------------------------------------------------------------------

def addparaqr():
    try:
        try:
            image = camcapture('qr', '', 40)
        except Exception as e:
            widgets.error("Failed to capture image for QR scan.")
            print(e)
            return

        detect = decode(image)
        qr_data = ''.join([obj.data.decode('utf-8') for obj in detect])

        if not qr_data:
            widgets.error("No QR code detected.")
            return

        results.usesummary("QR code scanned and decoded for: " + qr_data)

        try:
            analyte, calid, caldate, expdate, unit, batchid, measl, measu = qr_data.split(';')
        except ValueError:
            widgets.error("QR code content is invalid or improperly formatted.")
            return

        if analyte == "HBA":
            analyte = "HbA1C"

        analytedb = TinyDB(deviceinfo.path + 'analytes.json')
        Sample = Query()

        if analytedb.search(Sample.batchid == batchid):
            widgets.error(f"Analyte '{analyte}' with batch ID '{batchid}' already exists.")
        else:
            utils.updatepara(analyte, calid, caldate, expdate, batchid, measl, measu, unit)
            results.usesummary(f"Calibration for '{analyte}' with batch ID '{batchid}' read from QR scan.")

    except Exception as e:
        traceback.print_exc()
        results.usesummary(e)
        widgets.error("Unexpected error occurred while adding analyte from QR.")

def calfit(conc_array, result_array, calid):
    try:
        details_cal = calid.split("/")
        p_factor = int(details_cal[0])

        cal_res = []

        if p_factor == 1:  # Linear
            const1 = float(details_cal[1]) / 100
            const2 = float(details_cal[2]) / 100
            cal_res = [const1 * float(c) + const2 for c in conc_array]

        elif p_factor == 2:  # Log-linear
            const1 = float(details_cal[1]) / 100
            const2 = float(details_cal[2]) / 100
            cal_res = [const1 * np.log(float(c)) + const2 for c in conc_array]

        elif p_factor == 3:  # Power curve
            const1 = float(details_cal[1]) / 100
            const2 = float(details_cal[2]) / 100
            cal_res = [pow(const1 * float(c), const2) for c in conc_array]

        else:  # 4PL
            a = float(details_cal[0]) / 100
            b = float(details_cal[1]) / 100
            c = float(details_cal[2]) / 100
            d = float(details_cal[3]) / 100
            for conc in conc_array:
                try:
                    k = pow(float(conc) / c, b)
                    h = (a - d) / (1 + k)
                    y = d + h
                    cal_res.append(y)
                except Exception as e:
                    print(f"Error in 4PL computation for {conc}: {e}")
                    cal_res.append(0)

        try:
            plt.plot(conc_array, cal_res, label="Fitted Curve")
            plt.plot(conc_array, result_array, label="Actual Data")
            plt.legend()
            plt.savefig(deviceinfo.path + f'qctests/calfit_{calid}.png')
            plt.close()
        except Exception as e:
            widgets.error("Could not generate calibration plot.")
            traceback.print_exc()
            results.usesummary(e)

        try:
            corr_matrix = np.corrcoef(cal_res, result_array)
            corr = corr_matrix[0, 1]
            R_sq = str(round(corr ** 2, 4))
        except Exception as e:
            results.usesummary(e)
            widgets.error("Could not calculate R².")
            traceback.print_exc()
            R_sq = 'Err'

        return R_sq

    except Exception as e:
        widgets.error("Error in calibration fitting.")
        traceback.print_exc()
        results.usesummary(e)
        return 'Err'



#-----------------------------------------------------------------------
