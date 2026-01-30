from picamera2 import Picamera2, Preview
from libcamera import Transform 
import time
import ast
from gpiozero import LED
import matplotlib.pyplot as plt
import numpy as np
import cv2
from PIL import Image
from tinydb import TinyDB, Query

from scipy.signal import find_peaks, peak_prominences, savgol_filter
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.ndimage import gaussian_filter1d
from pyzbar.pyzbar import decode
import os

import widgets
import deviceinfo
import results
import utils
import traceback
import paneltestutils

def camcapture(sampleid, date, gpio_pin_board):
    # Mapping from BOARD to BCM numbering for the specified pins
    BOARD_TO_BCM = {40: 21, 29: 5}
    if gpio_pin_board not in BOARD_TO_BCM:
        raise ValueError(f"Unsupported BOARD pin: {gpio_pin_board}. Use 29 or 40.")
    bcm_pin = BOARD_TO_BCM[gpio_pin_board]

    image_folder = 'captured'
    
    # Initialize hardware objects
    light = LED(bcm_pin)

    # Construct the image path
    image_path = os.path.join(deviceinfo.path, image_folder)
    os.makedirs(image_path, exist_ok=True)
    image_filename = f'capturedimage_pil_{sampleid}_{date}.jpg'
    full_path = os.path.join(image_path, image_filename)
    
    max_attempt = 3
    for attempt in range(1, max_attempt +1):
        picam2= None
        should_retry = False
        try:
            results.usesummary("Starting camera capture...")
            light.on() #Turn on LED and
            picam2 = Picamera2()
            
            # Configure the camera for a still capture
            config = picam2.create_preview_configuration(main={"size":(3280,2464),"format": "YUV420"},lores={"size":(650,480),"format": "YUV420"},display= "lores" ) #(3280,2464)640,480
            picam2.configure(config)        #  start the camera to apply settings
            picam2.start()
            time.sleep(2)
#             while True:
#                 yuv420 = picam2.capture_array("main")
#                 rbg = cv2.cvtColor(yuv420,cv2.COLOR_YUV420p2RGB)
#                 cv2.imwrite(full_path+"YUV",rbg)
            picam2.stop_preview()
            picam2.start_preview(Preview.QTGL)
    #         picam2.start()
            time.sleep(2)
            picam2.capture_file(full_path)
#             yuv420 = cv2.imread(full_path)
#             rbg = cv2.cvtColor(yuv420,cv2.COLOR_YUV420p2RGB)
#             cv2.imshow("camera",rgb)
#             cv2.imwrite(full_path+"YUV",rbg)
            if os.path.exists(full_path) and os.path.getsize(full_path) > 1024:
                image_pil = Image.open(full_path)
                image_rs = image_pil.resize((800,480),Image.Resampling.LANCZOS)
                numpy_img = np.array(image_rs)
                image_cv2 = cv2.cvtColor(numpy_img,cv2.COLOR_RGB2BGR)
                image_filename = f'capturedimage_{sampleid}_{date}.jpg'
                full_path = os.path.join(image_path, image_filename)
                cv2.imwrite(full_path,image_cv2)
                input_image = cv2.imread(full_path)
                light.off()
                light.close()
                results.usesummary(f"Image saved to: {full_path}")
                print(attempt, "line80")
                return input_image
            else:
                results.usesummary(f"Attempt {attempt}: Catured file was empty/missing")
                should_retry = True
        except OSError as e:
            if e.errno ==12 or "allocate" in str(e).lower():
                results.usesummary(f"Memory Error (OSError) on attempt {attempt}: {e}")
                print(attempt, "line88")
                should_retry = True
            else:
                 results.usesummary(f"Hardware/OS Error on attempt {attempt}: {e}")
                 print(attempt, "line91")
                 should_retry = False
        except Exception as e:
            err_msg = str(e).lower()
            if any(k in err_msg for k in ["memory","allocate","dma","buffer","resources"]):
                 results.usesummary(f"Buffer allocation error on attempt {attempt}: {e}")
                 print(attempt, "line86")
                 should_retry = True
            else:
                 results.usesummary(f"Unexpected Error on attempt {attempt}: {e}")
                 should_retry = False
                 print(attempt, "line86")
        finally:
            if picam2:
                try:
                    if picam2.started:
                        picam2.stop()
                    picam2.close()
                    light.close()
                    
                except:
                    pass
        if not should_retry:
            results.usesummary("Stopping retries due to fatal error or sucess.")
            print(attempt, "line114")
            break
        if attempt < max_attempt:
            results.usesummary("retrying...")
            time.sleep(1)
        if light:
            light.close()
    results.usesummary("All capture attempts failed.")
    return None
            
# def camcapture(sampleid, date, gpio_pin_board):
#     # Mapping from BOARD to BCM numbering for the specified pins
#     BOARD_TO_BCM = {40: 21, 29: 5}
#     if gpio_pin_board not in BOARD_TO_BCM:
#         print(f"Unsupported BOARD pin: {gpio_pin_board}. Use 29 or 40.")
#     bcm_pin = BOARD_TO_BCM[gpio_pin_board]
# 
#     image_folder = 'captured'
#     
#     # Initialize hardware objects
#     picam2 = Picamera2()
#     light = LED(bcm_pin)
# 
#     # Construct the image path
#     image_path = os.path.join(deviceinfo.path, image_folder)
#     os.makedirs(image_path, exist_ok=True)
#     image_filename = f'capturedimage_pil_{sampleid}_{date}.jpg'
#     full_path = os.path.join(image_path, image_filename)
# 
#     try:
#         results.usesummary("Starting camera capture...")
#         light.on() #Turn on LED and
#         
#         # Configure the camera for a still capture
#         config = picam2.create_preview_configuration(main={"size":(3280,2464)},lores={"size":(3280,2464)})
#         picam2.configure(config)      
#         picam2.start_preview(Preview.QT)
#         picam2.start()
#         time.sleep(2)
#         picam2.capture_file(full_path)
#         
#         results.usesummary(f"Image saved to: {full_path}")
# 
#     except Exception as e:
#         traceback.print_exc()
#         results.usesummary(f"Error during camera operation: {e}")  
# 
#     finally:
#         if picam2.started:
#             picam2.stop()
#         picam2.close()
#         light.close()
# 
#     image_pil = Image.open(full_path)
#     image_rs = image_pil.resize((800,480),Image.Resampling.LANCZOS)
#     numpy_img = np.array(image_rs)
#     image_cv2 = cv2.cvtColor(numpy_img,cv2.COLOR_RGB2BGR)
#     image_filename = f'capturedimage_{sampleid}_{date}.jpg'
#     full_path = os.path.join(image_path, image_filename)
#     cv2.imwrite(full_path,image_cv2)
#     input_image = cv2.imread(full_path)
#     if input_image is None:
#         results.usesummary(f"Image not found or unreadable at: {full_path}")
#         widgets.error("80 Error in croping the roi")
# #         raise FileNotFoundError(f"Image not found or unreadable: {full_path}")
#         
#     return input_image
# 
#---------------------------------------------------picam----------------------------------------------------------------
# def camcapture_picam(sampleid, date, gpio_no):
#     preview_time=3
#     image_folder='captured'
#     camera = PiCamera()
#     image_path = os.path.join(deviceinfo.path, image_folder)
#     os.makedirs(image_path, exist_ok=True)
#     image_filename = f'capturedimage_{sampleid}_{date}.jpg'
#     full_path = os.path.join(image_path, image_filename)

#     GPIO.setwarnings(False)
#     GPIO.setmode(GPIO.BOARD)
#     GPIO.setup(gpio_no, GPIO.OUT)

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
#         traceback.print_exc()
#         results.usesummary(f"Error during camera operation: {e}")
#         raise
#     finally:
#         camera.close()
#         GPIO.cleanup()

#     input_image = cv2.imread(full_path)
#     if input_image is None:
#         results.usesummary(f"Image not found or unreadable at: {full_path}")
#         raise FileNotFoundError(f"Image not found or unreadable: {full_path}")    
#     return input_image
#---------------------------------------------------picam----------------------------------------------------------------
 
def find_lfa(image, sampleid, date):
    roi = None
    try:
        if image is None:
            results.usesummary("Invalid image input: image is None")
#         raise ValueError("Invalid image input")
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
#             return None

        cassette_contour = max(contours, key=cv2.contourArea, default=None)

        if cassette_contour is None:
            results.usesummary("No valid cassette contour detected.")
#             return None

        perimeter = cv2.arcLength(cassette_contour, True)
        # print(perimeter)
        if not (1000 <= perimeter <= 3000): #changed upper limit to 3000(it was 2000) for meril
            results.usesummary(f"Cassette contour perimeter {perimeter} not in expected range (1000–2000).")
#             return None

        x, y, w, h = cv2.boundingRect(cassette_contour)
        aspect_ratio = round(float(w) / h, 2)
        # print("aspect_ratio",aspect_ratio)
        if not (0.5 <= aspect_ratio <= 0.85):
            results.usesummary(f"Aspect ratio {aspect_ratio} not in expected range (0.6–0.85).")
#             return None

        roi = image[y:y + h, x:x + w]
        save_dir = os.path.join(deviceinfo.path, 'captured')
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f'test_cassette_{sampleid}_{date}.jpg')
        cv2.imwrite(save_path, roi)
        results.usesummary(f"ROI successfully saved: {save_path}")
#         return roi
    except Exception as e:
        traceback.print_exc()
        widgets.error(str(e))
        results.usesummary(f"Error in find_lfa: {str(e)}")
    return roi

def find_testwindow(img, sampleid, date):
    roi_image = None
    image = img[:,80:-80]
    image = image.copy()
    
    # Preprocess image: blur and grayscale
    blurred = cv2.GaussianBlur(image, (9, 9), 0)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    kernel = np.ones((5, 5), np.uint8)
    
    # Sobel edge detection (x and y gradients)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    
    abs_grad_x = cv2.convertScaleAbs(sobelx)
    abs_grad_y = cv2.convertScaleAbs(sobely)
    # Weighted sum of gradients to emphasize edges
    grad = cv2.addWeighted(abs_grad_x, 0.2, abs_grad_y, 0.2, 0) 
    
    # Threshold using Otsu's method to binarize edges
    ret, thresh = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = thresh.astype(np.uint8)
   
    # Find contours on thresholded image
    contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    test_window_cnt = image.copy()
    cleaned_contours =[]
    for contour in contours:
        print(cv2.contourArea(contour))
        if cv2.contourArea(contour) > 1000:
            print('tw',cv2.contourArea(contour))
            cleaned_contours.append(contour)
    cv2.drawContours(test_window_cnt, cleaned_contours,-1,(0,255,0),2)
    cv2.imwrite(deviceinfo.path+'/captured/contours.jpg',test_window_cnt)
    rect_candidates = []

    img_height, img_width = gray.shape
    for contour in cleaned_contours:
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) >= 4:
            x, y, w, h = cv2.boundingRect(approx)
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 300:
                aspect_ratio = w / float(h) if h != 0 else 0
                # print("Selected peri PR:", perimeter, "AR: ", aspect_ratio, "TH: ", h,w)
                if 0.1 <= aspect_ratio <= 0.98:
                    if 100 <= h <= 300 : # Reverify this h 
                        area = h * w
                        print("Selected rect PR:", perimeter, "AR: ", aspect_ratio, "TH: ", h,w)
                        rect_candidates.append((x, y, w, h, area, contour))
    try:
        if rect_candidates:
            # Sort by area descending to pick largest candidate
            rect_candidates.sort(key=lambda r: r[4], reverse=True)
            x1, y1, w1, h1, area, best_contour = rect_candidates[0]
            # print(h1)
            roi_image = image.copy()
            roi_image = roi_image[y1:y1 + h1, x1:x1 + w1]
            cv2.imwrite(deviceinfo.path + f'captured/roi_{sampleid}_{date}.jpg', roi_image)
    except Exception as e:
        traceback.print_exc()
        print(e)
        results.usesummary(f"Warning: Failed to save cassette image: {str(e)}")
        widgets.error(f"Error processing test window")
    return roi_image


#Meril Drug of Abuse test finding protocol
def process_doa_image(total_tests,image, sampleid, date):
    """
    Detects the DOA cassette, saves the ROI, and extracts exactly n test strips.
    Returns a list of 5 cropped test strip images, or None if extraction fails.
    """
    test_crops = None
    try:
        if image is None:
            results.usesummary("Invalid Image input")
#             raise ValueError("Invalid image input: image is None")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel_cassette = np.ones((11, 11), np.uint8)
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_cassette, iterations=2)
        contours = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        image1 = image.copy()
        cv2.drawContours(image1,contours,-1,(0,255,0),2)
        cv2.imwrite(deviceinfo.path+'/captured/test_cassate_cnt.jpg',image1)
        if not contours:
            ""
#             raise ValueError("No contours found for cassette detection")
        cassette_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(cassette_contour)
        
        print("cassette_image",x,y,w,h, len(cassette_contour))
        cassette_image = image[y:y+h, x:x+w]
        try:
            save_dir = os.path.join(deviceinfo.path, 'captured')
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f'test_cassette.jpg')
            cv2.imwrite(save_path, cassette_image)
            results.usesummary(f"ROI successfully saved: {save_path}")
        except Exception as save_err:
            traceback.print_exc()
            results.usesummary(f"Warning: Failed to save cassette image: {str(save_err)}")
        x,y,_ = cassette_image.shape
        bottom_height = 650
        test_window = cassette_image[x-bottom_height:x-20,:] #hinged from the bottom for consistent cropping
        c_gray = cv2.cvtColor(test_window, cv2.COLOR_BGR2GRAY)
        c_blurred = cv2.GaussianBlur(c_gray, (7, 7), 0)
        sobelx = cv2.Sobel(c_blurred,cv2.CV_64F,1,0,ksize=5)
        sobely = cv2.Sobel(c_blurred,cv2.CV_64F,0,1,ksize=5)
        abs_grad_x = cv2.convertScaleAbs(sobelx)
        abs_grad_y = cv2.convertScaleAbs(sobely)
        grad = cv2.addWeighted(abs_grad_x,0.05,abs_grad_y,0.05,0)
        _,c_thresh = cv2.threshold(grad,0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        kernel_test = np.ones((11, 11), np.uint8)
        morph = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, kernel_test, iterations=2)
        test_window_cnt = test_window.copy()
        test_contours = cv2.findContours(c_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        cleaned_contours =[]
        for contour in test_contours:
            if cv2.contourArea(contour) > 3000:
                cleaned_contours.append(contour)
        cv2.drawContours(test_window_cnt, cleaned_contours,-1,(0,255,0),2)
        cv2.imwrite(deviceinfo.path+'/captured/doa_contours.jpg',test_window_cnt)
#         test_rects = []
#         image_rect = test_window.copy()
#         for contour in cleaned_contours:
#             epsilon = 0.01*cv2.arcLength(contour,True)
#             approx = cv2.approxPolyDP(contour,epsilon,True)
#             if len(approx)>=4:
#                 perimeter = cv2.arcLength(contour, True)
#                 if perimeter > 300:
#                     tx, ty, tw, th = cv2.boundingRect(contour)
#                     aspect_ratio = tw / float(th) if th != 0 else 0
# #                     print("perimeter",perimeter,"aspect_ratio",aspect_ratio,"th",th,"tw",tw)
#                     if 0.1 <= aspect_ratio <= 0.98:
#                         if th >100 and tw <=150:
#                             test_rects.append((tx, ty, tw, th))
#                             print("selected PR: ",perimeter,"AR: ",aspect_ratio,"th: ",th,"tw: ",tw)
#                             print("--------------------------------------------------------------------------")
#                             cv2.rectangle(image_rect,(tx,ty),(tx+tw,ty+th),(255,0,0),2)
        candidate_rects =[]
        for contour in cleaned_contours:
            tx,ty,tw,th = cv2.boundingRect(contour)
            if th > (test_window.shape[0]*0.4):
                candidate_rects.append([tx,ty,tw,th])
            if len(candidate_rects)>0:
                widths = sorted([r[2] for r in candidate_rects])
                median_w = widths[len(widths)//2]
                max_width_thresh = median_w*1.2
                
                final_crops = []
                candidate_rects.sort(key=lambda r:r[0])
                for i, (tx,ty, tw, th) in enumerate(candidate_rects):
                    current_crop = None
                    if tw >max_width_thresh:
                        if i == 0:
                            diff = tw-median_w
                            new_tx = tx+diff
                            current_crop = test_window[ty:ty+th, new_tx:new_tx+median_w]
                        elif i == len(candidate_rects)-1:
                            current_crop = test_window[ty:ty+th, tx:tx+median_w]
                        else:
                            center_x = tx +(tw//2)
                            half_median = median_w//2
                            new_tx = center_x-half_median
                            if new_tx<tx: new_tx = tx
                            current_crop = test_window[ty:ty+th, new_tx:new_tx+median_w]
                    else:
                        current_crop = test_window[ty:ty+th, tx:tx+tw]
                    final_crops.append(current_crop)          
#         save_path = os.path.join(save_dir, f'{sampleid}_{date}_rect.jpg')
#         cv2.imwrite(save_path, image_rect)
        if len(final_crops) != total_tests: 
            err_msg = f"Expected {total_tests} test windows but found {len(final_crops)}. Re-insert test card properly and try again."
            results.usesummary(err_msg)
            widgets.error(err_msg)
        else:
#             final_crops.sort(key=lambda r: r[0])
            test_crops = []
            i = 0 
            for c in final_crops:
#                 test_crops.append(test_window[ty:ty + th, tx:tx + tw])
                test_crops.append(c)
                save_path = os.path.join(save_dir, f'test_{i}.jpg')
                cv2.imwrite(save_path, c)
                i+=1
    except Exception as e:
        traceback.print_exc()
        err_msg = f"An error occurred during processing: {str(e)}"
        results.usesummary(err_msg)
        widgets.error("Image processing failed. Please check device and try again.")
    return test_crops

def roi_segment(captured_image, sampleid, date):
    roi_seg = None
    try:
        test_cassette = find_lfa(captured_image, sampleid, date)
        if test_cassette is not None:
            test_window = find_testwindow(test_cassette, sampleid, date)
            if test_window is not None:
                roi_seg = test_window
            else:
                ""
#                 widgets.error("Re-insert the test cassette and try again")
        else:
            widgets.error("Test cassette not detected.")
    except Exception as e:
        traceback.print_exc()
        # widgets.error(f"Error in ROI segmentation: {e}")
        results.usesummary(f"Error in roi_segment: {e}")
    return roi_seg


def get_prominences(result_array, sampleid, date):
    try:
        # Preprocess and baseline correction
        print('len',len(result_array), len(result_array))
        inverted_data = 0 - result_array  # invert signal
        baseline = baseline_correction(inverted_data, 2000, 0.005) #changed 2000, 0.005 to 1500,0.001
        corrected_data = inverted_data - baseline        
        pr_val = int(deviceinfo.peak_threshold)
        peaks, properties = find_peaks(corrected_data,height=0, prominence=pr_val, width=(4,20),rel_height=0.30,distance=25)
        prominences = peak_prominences(corrected_data, peaks)[0]
        results.usesummary(f"Detected prominences: {prominences}")

        # Plot and save peak detection result
        plt.plot(corrected_data, label='Baseline corrected data')
        plt.plot(peaks, corrected_data[peaks], 'x', label='Detected peaks')
        plt.legend()
        plt.savefig(f"{deviceinfo.path}captured/peaks_{sampleid}_{date}.png")
        plt.close()
        return peaks, prominences

    except Exception as e:
        traceback.print_exc()
        results.usesummary(f"Error in get_prominences: {e}")
        # widgets.error(f"Error in prominence detection: {e}")
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

def filter_result_array(result_array, window=10):
    data = np.array(result_array)
    differences = np.abs(np.ediff1d(data))

    if len(differences) < window:
        results.usesummary("filter_result_array: Not enough data to filter meaningfully.")
        return data

    max_diff_index = np.argmax(differences[:window])
    results.usesummary(f"filter_result_array: Max difference at index {max_diff_index}")

    start_index = max_diff_index + 30
    end_index = -28 if len(data) > 20 else len(data)
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

def check_bg(test_window, sampleid, date): #why are we checking the background
    flag = 0 
    if test_window is None:
        return flag
    try:
        img_cmy = rgb2cmk(test_window)
        _, m, _ = cv2.split(img_cmy)

        hist = cv2.calcHist([m], [0], None, [256], [0, 256])
        hist_smooth = savgol_filter(hist[:, 0], 21, 2)

        #if already hist is being plotted do we need to add peaks logic to identify background
        peaks, _ = find_peaks(hist_smooth, distance=40, prominence=80, width=(5, 50))
        prominences = peak_prominences(hist_smooth, peaks)[0]
        plt.plot(hist_smooth)
        plt.plot(peaks,hist_smooth[peaks],'x',"bg")
#         plt.savefig(f"{deviceinfo.path}captured/bg_{sampleid}_{date}.png")
        plt.close()

        if len(prominences) > 1:
            flag = 1
            results.usesummary(f"{sampleid} has high background.")
        else:
            results.usesummary(f"{sampleid} doesn't have high background.")
        print('check_bg',flag)

    except Exception as e:
        traceback.print_exc()
        err_msg = f"Error occurred while reading background: {e}"
        results.usesummary(err_msg)
        # widgets.error(err_msg)
        
    return flag

def val_qualitative(peaks, prominences, bg_flag, analyte, sampleid, date, ordered_marker_array):
    m_array = ordered_marker_array
    value = "None"
    try:
        if len(prominences) >3:
            value = "Err03: high background"
        elif len(prominences) == 0:
            value = "Err 02: No control line."
        else:
            num_lines = len(prominences)
            num_markers = len(m_array)
            if num_markers == 1:
                if num_lines == 3:
                    value = "Err03: high background."
                else:
                    value = f"Positive for {m_array[0]}" if num_lines == 2 else f"Negative for {m_array[0]}"
            elif num_markers == 2:
                if num_lines == 3:
                    value = f"Positive for {m_array[0]} and {m_array[1]}"
                elif num_lines == 2:
                    if (peaks[1] - peaks[0]) < 50: #check the distance for meril
                        value = f"Positive for {m_array[0]}"
                    else:
                        value = f"Positive for {m_array[1]}"
                else:
                    value = f"Negative for {m_array[0]} and {m_array[1]}"
    except Exception as e:
        traceback.print_exc()
        value = "Err 11: Exception in qualitative analysis"
        results.usesummary(f"Exception occurred in val_qualitative: {e}")
    results.usesummary(f"Qualitative result for [{analyte}] is [{value}]")
    return value

def val_qualitative_competitive(peaks, prominences, bg_flag, analyte, sampleid, date, ordered_marker_array):
    m_array = ordered_marker_array
    value = "None"
    try:
        if len(prominences) > 3:
            value = "Err03: high background."
        elif len(prominences) == 0:
            value = "Err 02: No control line."
        else:
            # --- Competitive Logic (Inverted) ---
            num_lines = len(prominences)
            num_markers = len(m_array)

            if num_markers == 1:
                if num_lines == 3:
                    value = "Err03: high background."
                else:
                # 1 line (Control only) means POSITIVE (what about faint lines?)
                    value = f"Positive for {m_array[0]}" if num_lines == 1 else f"Negative for {m_array[0]}"
            elif num_markers == 2:
                if num_lines == 1: # Control only
                    value = f"Positive for {m_array[0]} and {m_array[1]}"
                elif num_lines == 2: # Control + 1 Test line
                    if (peaks[1] - peaks[0]) < 100: # T1 is PRESENT => (Negative)
                        value = f"Negative for {m_array[0]}, Positive for {m_array[1]}"
                    else: # T2 is PRESENT => (Negative)
                        value = f"Positive for {m_array[0]}, Negative for {m_array[1]}"
                elif num_lines == 3: # Control + 2 Test lines
                    value = f"Negative for {m_array[0]} and {m_array[1]}"
                    
    except Exception as e:
        traceback.print_exc()
        value = "Err 11: Exception in qualitative analysis"
        results.usesummary(f"Exception occurred in val_qualitative: {e}")

    results.usesummary(f"Qualitative result for [{analyte}] is [{value}]")
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
            traceback.print_exc()
            results.usesummary("No results overwritten.")

    # Capture image
    captured_image = camcapture(sample_id, date, 40)
    results.usesummary("Image Captured.")

    try:
        print(analyte)
        loaded_doa_panels = paneltestutils.load_panel_tests()
        doa_panels_lower = {panel.lower(): panel for panel in loaded_doa_panels}
        analyte_lower = analyte.lower()
        if analyte_lower in doa_panels_lower:
            format_val = lambda res:"+Ve" if res.startswith("Positive") else ("-Ve" if res.startswith("Negative") else res)
            panel_name = doa_panels_lower[analyte_lower]
            # **CRITICAL CHANGE:** Use the dictionary loaded from the database
            total_tests = loaded_doa_panels[panel_name] 
            test_keys = list(total_tests.keys())
            test_crops = process_doa_image(len(total_tests), captured_image, sample_id, date)
            if test_crops is None:
                widgets.error("Failed to extract test strips from cassette")
            if total_tests is None:
                widgtes.error(f"DOA Panel is not defined in the 'Drug_of_Abuse' dictionary in info.py.")
#                 raise ValueError(f"DOA Panel is not defined in the 'Drug_of_Abuse' dictionary in info.py.")
            elif len(total_tests) != len(test_crops):
                widgets.error(f"Expected {len(total_tests)} test windows, but got {len(test_crops)}")
#                 raise ValueError(f"Expected {len(total_tests)} test windows, but got {len(test_crops)}")
            panel_results = {}
            
            for i,test_crop in enumerate(test_crops):
                test_strip_id = f"{sample_id}_{i}"
                current_ti = test_keys[i]
                current_markers = total_tests[current_ti]
                bg_flag = check_bg(test_crop, sample_id, date)
                result_array = scan_card(test_crop)
                peaks, prominences = get_prominences(result_array[5:-15], test_strip_id, date)
                
                result_for_strip  = val_qualitative_competitive(peaks, prominences, bg_flag, analyte, test_strip_id, date, current_markers) 
                for marker in current_markers:
                    panel_results[marker] = format_val(result_for_strip)
            val = panel_results
#             val = ",".join(f"'{marker}':{result}" for marker, result in panel_results.items())
            # print('doa',type(val),panel_results)
            results.usesummary(f"DOA result for [{sample_id}] is [{val}]")
        else:          
            # ROI and background setup
            roi_seg = roi_segment(captured_image, sample_id, date)
            # print(type(roi_seg))
            bg_flag = check_bg(roi_seg, sample_id, date)
            result_array = scan_card(roi_seg)
            result_array = filter_result_array(result_array)
            peaks, prominences = get_prominences(result_array[:], sample_id, date)
            # Handle qualitative tests
            ordered_marker_array = deviceinfo.qualitative_dict[data_array[1]]
            val = val_qualitative(peaks, prominences, bg_flag, analyte, sample_id, date, ordered_marker_array)
    except Exception as e:
        traceback.print_exc()
#         widgets.error("Error occurred while reading the test.")
        results.usesummary(e)
    try:
        if "back" in data_array[1].lower():
#             val = ast.literal_eval(val)
            res = data_array[3]
            res.update(val)
            data_array[3] = res
        else:
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
        # widgets.error("Could not add result to database.")
#--------------------------------------------------------------------------
def addparaqr():
    try:
        image = camcapture('qr', '', 40)
        detect = decode(image)
        qr_data = ''.join([obj.data.decode('utf-8') for obj in detect])
        if not qr_data:
            ""
#             widgets.error("No QR code detected.")
        results.usesummary("QR code scanned and decoded for: " + qr_data)
        analyte, calid, caldate, expdate, unit, batchid, measl, measu = qr_data.split(';')
        widgets.error("QR code content is invalid or improperly formatted.")
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
        print(e)
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

#--------------------------------------------------------------------------
