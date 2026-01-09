import os
import glob
import re
import pandas as pd

def get_newest_file(directory, base_pattern):
    search_pattern = os.path.join(directory, base_pattern + "*.xlsx")
    files = glob.glob(search_pattern)
    
    if not files:
        return None
        
    regex = re.compile(r"Component(\d+)(?:[- ]\(?(\d+)\)?)?\.xlsx$")
    max_version_tuple = (-1, -1)
    newest_file = None
    
    for file_path in files:
        match = regex.search(file_path)
        if match:
            main_ver = int(match.group(1))
            sub_ver = int(match.group(2)) if match.group(2) else 0
            current_version_tuple = (main_ver, sub_ver)
            if current_version_tuple > max_version_tuple:
                max_version_tuple = current_version_tuple
                newest_file = file_path
    return newest_file

def main():
    downloads_dir = "/Users/mjanda/Downloads"
    base_name_pattern = "EmployeesFullData-Page1-Component"
    
    file_path = get_newest_file(downloads_dir, base_name_pattern)
    if not file_path:
        print("No file found.")
        return

    print(f"Inspecting file: {file_path}")
    try:
        # Load header from row index 2 (0-based) as per previous script
        df = pd.read_excel(file_path, header=2, nrows=0) 
        print("Columns found:")
        for col in df.columns:
            print(f"- {col}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
