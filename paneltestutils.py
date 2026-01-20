from typing import Dict, List, Any
from tinydb import TinyDB, Query
import tkinter as tk
from tkinter import filedialog
import subprocess
from datetime import datetime
import numpy as np
from pyzbar.pyzbar import decode
import time
import importlib
import shutil
import webbrowser
import widgets
import exitprocess
import deviceinfo
import os
import json
import csv
import results
import imagepro
import utils
import re
import traceback


def validate_start_config(panel_name: str, max_slots: str, sides: str, batch_id: str, exp_date: str) -> bool:
    """
    Validates all mandatory inputs from the initial configuration screen.
    Returns True if valid, shows error via widgets.error() if invalid.
    """
    if not panel_name or panel_name in ["New Panel Name"]:
        widgets.error("Panel Name cannot be empty or the default placeholder.")
        return False
        
    if max_slots not in ['4', '5', '6', '8', '10', '12']:
        widgets.error("Please select a valid maximum number of test slots.")
        return False

    if not batch_id:
        widgets.error("Batch ID is a mandatory field.")
        return False

    date_pattern = re.compile(r'^\d{2}/\d{2}$')
    if not date_pattern.match(exp_date):
        widgets.error("Expiration date format must be MM/YY.")
        return False
        
    if sides not in ['Single', 'Two-Sided']:
        widgets.error("Panel Sides selection is missing.")
        return False

    return True

def validate_slot_selection(config_state,marker_count: str, marker1: str, marker2: str, current_slot: int) -> str:
    """
    Validates that markers are selected based on the radio button choice.
    
    Returns: 
        An empty string ("") if valid, otherwise returns the error message string.
    """
    side_key = config_state['side']
    configured_slots=config_state['configured_slots'].get(side_key,{})
    all_markers =[]
    for slot_config in configured_slots.values():
        all_markers.extend(slot_config)
    current_markers = all_markers
    if marker_count == "1":
        # Check if the marker variable is empty or still holds the default placeholder text
        if not marker1 or marker1.startswith("Select"):
            widgets.error(f"T{current_slot}: Please select Marker 1.")
            return False
        if marker1 in current_markers:
            widgets.error(f"T{current_slot}: Marker 1 ({marker1}) is already added in this panel.")
            return False
            
    elif marker_count == "2":
        # Check if either marker is missing or holds the default placeholder text
        if not marker1 or marker1.startswith("Select") or not marker2 or marker2.startswith("Select"):
            widgets.error(f"T{current_slot}: Please select both markers.")
            return False
        if marker1 == marker2:
            widgets.error(f"T{current_slot}: Marker 1 and Marker 2 cannot be the same.")
            return False
        for marker in [marker1,marker2]:
            if marker in current_markers:
                widgets.error(f"T{current_slot}:Marker {marker} is already added.")
                return False
            
    
    return  True # Valid

def save_current_slot(config_state: Dict[str, Any], marker_count: str, marker1: str, marker2: str) -> None:
    """
    Saves the configuration for the current T-slot into the config_state dictionary.
    NOTE: This function assumes the calling UI function has ALREADY validated the input.
    """
    slot_name = f"T{config_state['current_slot']}"
    slot_analytes = []
    
    if marker_count == "1":
        slot_analytes.append(marker1)
        
    elif marker_count == "2":
        slot_analytes.extend([marker1, marker2])

    # Store the result for the current side (FRONT or BACK)
    side_key = config_state['side']
    if side_key not in config_state['configured_slots']:
        config_state['configured_slots'][side_key] = {}
        
    config_state['configured_slots'][side_key][slot_name] = slot_analytes



def advance_or_finalize_panel(config_state: Dict[str, Any]) -> str:
    config_state['current_slot'] += 1
    
    if config_state['current_slot'] <= config_state['total_slots']:
        return 'NEXT_SLOT'
        
    # Current side is complete
    if config_state['sides'] == 'Two-Sided' and config_state['side'] == 'FRONT':
        config_state['side'] = 'BACK'
        config_state['current_slot'] = 1
        return 'FLIP_SIDE'  
    return 'COMPLETE'


def finalize_and_save_panels(config_state: Dict[str, Any], batch_id: str, exp_date: str) -> str:   
    if not config_state.get('configured_slots', {}):
        return "Cannot save panel: No marker configurations found."    
    # 1. Initialize TinyDB access
    try:
        panel_db = TinyDB(deviceinfo.path+'panel_tests.json')
    except Exception as e:
        traceback.print_exc()
        return f"Failed to initialize TinyDB for panels: {e}" 
    panels_to_save = []
    panel_name_base = config_state['panel_name']
    # Base metadata for the new documents
    base_metadata = {
        'batch_id': batch_id, 
        'exp_date': exp_date,
    }
    

    # 2. Format the new panels into TinyDB documents
    if config_state['sides'] == 'Single':
        panel = {
            'panel_name': panel_name_base,
            'config': config_state['configured_slots'].get('FRONT', {}),
            **base_metadata # Merge metadata
        }
        panels_to_save.append(panel)
    else:
        front_data = config_state['configured_slots'].get('FRONT', {})
        back_data = config_state['configured_slots'].get('BACK', {})
        
        if not front_data or not back_data:
            widgets.error(f"Missing data for either the FRONT or BACK side")
            return "Cannot save two-sided panel: Missing configurations for either the FRONT or BACK side."

        # Front Side Document
        panels_to_save.append({
            'panel_name': f"{panel_name_base}-FRONT",
            'config': front_data,
            **base_metadata
        })
        # Back Side Document
        panels_to_save.append({
            'panel_name': f"{panel_name_base}-BACK",
            'config': back_data,
            **base_metadata
        })

    try:
        for panel in panels_to_save:
            # The structure of the stored data is:
            # { "panel_name": "DADP6", "config": {...}, "batch_id": "B001", "exp_date": "12/25" }
            panel_db.insert(panel)
            analyte = panel['panel_name']
            utils.updatepara(analyte, "1/1/1/1", " ", exp_date, batch_id," ", " ", "")
    except Exception as e:
        traceback.print_exc()
        return f"Failed to save panels to TinyDB: {e}"
    return "" # Success


def load_panel_tests():
    loaded_panels: Dict[str,Dict[str, List[str]]]={}
    db = TinyDB(deviceinfo.path+'panel_tests.json')
    panel_list = db.all()
    for panel in panel_list:
        panel_name = panel.get('panel_name')
        config = panel.get('config')
        if panel_name and config: 
            loaded_panels[panel_name] =config
    return loaded_panels



def panel_result1(prefix_Text, results_dict, column_width=25):  # Increased default width for better formatting
    if not isinstance(results_dict, dict):
        return f"{prefix_Text} Invalid results format"
        
    results_list = list(results_dict.items())
    num_results = len(results_list)
    output_lines = []
    header_indent = " " * len(prefix_Text) if prefix_Text else " " * 9
    
    for i in range(0, num_results, 2):
        prefix = str(prefix_Text) if i == 0 else header_indent
        line = prefix
        
        # First column
        if i < num_results:
            analyte1, result1 = results_list[i]
            # Truncate long error messages
            display_result1 = result1.split(':')[0] + '...' if len(result1) > 15 and ':' in result1 else result1
            col1 = f"{analyte1}: {display_result1}".ljust(column_width)
            line += col1
        
        # Second column
        if i + 1 < num_results:
            analyte2, result2 = results_list[i + 1]
            # Truncate long error messages
            display_result2 = result2.split(':')[0] + '...' if len(result2) > 15 and ':' in result2 else result2
            line += f"{analyte2}: {display_result2}"
            
        output_lines.append(line)
    
    if not output_lines:
        return f"{prefix_Text} No results available"
        
    return "\n".join(output_lines)

def panel_result(prefix_Text, results_dict, column_width=28):
    results_list = list(results_dict.items())
    num_results = len(results_list)
    output_lines = []
    header_indent = " " * 10
    pairwidth = column_width*2
    
    for i in range(0, num_results, 2):
        prefix = str(prefix_Text) if i == 0 else header_indent
        if i < num_results:
            analyte1, result1 = results_list[i]
            col1 = f"{analyte1}: {result1}".ljust(column_width)
        else:
            col1 = " ".ljust(column_width) 
        if i + 1 < num_results:
            analyte2, result2 = results_list[i + 1]
            col2 = f"{analyte2}: {result2}"
        else:
            col2 = " "
        col = (prefix+col1+col2).ljust(pairwidth)
        output_lines.append(col)
#         output_lines.append(prefix + col1 + col2)
    if not output_lines:
        return "Results: No data available."
    return "\n".join(output_lines)