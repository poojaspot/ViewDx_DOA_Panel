import pandas as pd
import io # Used to simulate file reading for demonstration

def validate_panel_csv(file_path: str) -> List[str]:
    """
    Validates the structure and content of the panel definition CSV file.

    Args:
        file_path (str): The path to the input CSV file.

    Returns:
        List[str]: A list of error messages. If the list is empty, the file is valid.
    """
    errors: List[str] = []
    
    # Use the original loading logic to read the file
    try:
        # Assuming only CSV files are loaded by the Tkinter part
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        errors.append(f"File not found at path: {file_path}")
        return errors # Stop if the file doesn't exist
    except Exception:
        # General I/O or parsing error (e.g., malformed lines)
        errors.append("CSV file could not be read. Check for non-standard characters or delimiters.")
        return errors

    # Standardize column names for checking
    df.columns = df.columns.astype(str).str.strip().str.upper()
    
    # 1. Check for required Panel_Name column
    if 'PANEL_NAME' not in df.columns:
        errors.append("Missing required header: 'Panel_Name'. Please ensure the first column is named 'Panel_Name'.")
        # Cannot proceed with content checks if Panel_Name is missing
        return errors 

    # 2. Check for missing test slot columns (T1, T2, etc.)
    test_columns = sorted([col for col in df.columns if col.startswith('T') and col[1:].isdigit()])
    if not test_columns:
        errors.append("No Test Slot columns found (T1, T2, etc.). Please ensure columns are named T1, T2, etc.")

    # 3. Check for rows with missing Panel_Name
    missing_panel_rows = df[df['PANEL_NAME'].isna() | (df['PANEL_NAME'].astype(str).str.strip() == '')]
    if not missing_panel_rows.empty:
        errors.append(f"Missing Panel Name in row(s): {list(missing_panel_rows.index + 2)}. Every panel must have a unique name.")
        
    # 4. Check for duplicate Panel_Name entries
    if df['PANEL_NAME'].duplicated().any():
        duplicates = df['PANEL_NAME'][df['PANEL_NAME'].duplicated()].unique()
        errors.append(f"Duplicate Panel Name(s) found: {', '.join(duplicates)}. Panel Names must be unique.")

    # 5. Check content errors in test slot columns
    for index, row in df.iterrows():
        row_num = index + 2  # +2 because index is 0-based and includes header row
        panel_name = row['PANEL_NAME']
        
        # Check if the entire panel row is empty (no analytes defined)
        has_analytes = any(pd.notna(row[col]) for col in test_columns)
        if not has_analytes and pd.notna(panel_name):
            errors.append(f"Row {row_num} (Panel: {panel_name}): No analytes defined. All T-slots are empty.")
            
        # Check for invalid delimiters (e.g., using commas instead of semicolons)
        for col in test_columns:
            cell_value = str(row[col]).strip()
            if pd.notna(row[col]):
                if ',' in cell_value:
                    errors.append(f"Row {row_num} (Panel: {panel_name}, Slot {col}): Used a COMMA (','). **Must use a SEMICOLON (';')** to separate analytes.")
                
    return errors