# ViewDX Software Update 

## Overview
updated by Pooja Mehta
aproved by:
    Date of updation: 11 April 2025
    
The software (`VIEW_03_0.0.1`) supports automated updates via a pendrive, including copying specific configuration fields and applying software patches.
Key features:
- Preserves user data and results fields (e.g., `qcstate`, `delstate`, `avail_mem`) on the device.
- Includes `updater.py` for pendrive-based software updates.
- Supports ROI function for LFA and automated result array trimming, which solves the issue with extra peak being detected due to edges of the lfa cassates.
- It also saves all the data in HL7 format.
- In the find_testwindow function, added a height cutoff of 265 pixels for the cropped rectangle.(This adjustment prevents detection of Veda Labs cassettes (test window 14.1 mm) due to their smaller size, while supporting Bhat Bio (15.5 mm), PSA from Bio-Footprints (15.3 mm), and our regular cassettes (15.9 mm).)



## Requirements


## Installation
NOTE: THE CURRENT VERSION OF THE INSTALLED VIEWDX DOESNOT HAVE FEATURES TO AUTOMATICALLY UPDATE THE SOFTWARE. THE servise person must copy the folder manually,
(make sure to keep the customer data, like lab_logo, deviceinfo.py results, hardwarescan, etc.)
0. Make sure to delete any old previous viewdx.zip folder from pendrive. 
1. Download viewdx.zip file and save it in pendrive. Make sure the name of the file is viewdx.zip and it is saved in pendrive directly not in anyother folder.
2. Start the device, Viewdx and let the software boot.
3. Insert pendrive with viewdx.zip to the the device, make sure pendrive is connected properly 
4. Go to "Settings" => "Data Backup & Update" => "Update Device from USB"
   