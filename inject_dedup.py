import os
import re

path = r'C:\Users\phone\Desktop\JobsCzInsight\public\index.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Rename const RAW_DATA to const RAW_DATA_SOURCE
# This prevents re-assignment errors since it is a const
if "const RAW_DATA = [{" in content:
    content = content.replace("const RAW_DATA = [{", "const RAW_DATA_SOURCE = [{")
    print("Renamed RAW_DATA to RAW_DATA_SOURCE.")

# 2. Inject Deduplication Logic
# We find the end of the RAW_DATA_SOURCE array (which ends with "];") and insert logic after it.
# A safe way is to find the first function definition or variable after the big data block.
# Or just append it immediately after the data block if we can find the closing bracket.

# Since regex matching a huge JSON array is risky/slow, I will look for the line that starts the next variable or function.
# Usually "const TOTAL_JOBS" or similar follows. 
# Let's search for the line "const TOTAL_JOBS =" (or similar usage) or just insert before the first function.

# Let's verify what follows RAW_DATA.
# Based on previous reads, it seems `const TOTAL_JOBS = RAW_DATA.length;` might be there or similar.

dedup_logic = """
        // ========== AUTOMATIC DATA DEDUPLICATION ==========
        function removeDuplicates(data) {
            const seen = new Set();
            return data.filter(item => {
                // Create a unique signature based on key fields
                const signature = `${item.role_type}|${item.company}|${item.city}|${item.seniority_level}|${item.avg_salary}|${item.contract_type}`;
                if (seen.has(signature)) {
                    return false;
                }
                seen.add(signature);
                return true;
            });
        }

        // Initialize RAW_DATA with unique records only
        const RAW_DATA = removeDuplicates(RAW_DATA_SOURCE);
        console.log(`Data Cleaning: Removed ${RAW_DATA_SOURCE.length - RAW_DATA.length} duplicates. Unique records: ${RAW_DATA.length}`);
"""

# Try to insert this right after RAW_DATA_SOURCE definition
# I'll look for the end of the line that defines RAW_DATA_SOURCE (it's one huge line usually).
# Since I replaced "const RAW_DATA = [{" with "const RAW_DATA_SOURCE = [{", I know where it starts.
# I will just insert the logic *before* the first function definition found after the data.

if "function" in content:
    # Find the first function *after* RAW_DATA_SOURCE
    # Actually, safely inserting before `const TOTAL_JOBS` or `window.onload` or `// ========== INITIAL RENDER` is better.
    
    # Let's look for `// ========== INITIAL RENDER` or `const SENIORITY_COLORS`
    target_marker = "const SENIORITY_COLORS" 
    
    if target_marker in content:
        content = content.replace(target_marker, dedup_logic + "\n        " + target_marker)
        print("Injected deduplication logic.")
    else:
        # Fallback: search for first function
        print("Warning: Could not find insertion point 'const SENIORITY_COLORS', looking for 'function'.")
        # This is risky if 'function' appears in the data string. 
        # Safer fallback: Append to the end of the file? No, needs to be before usage.
        
        # Let's try to find where `TOTAL_JOBS` is defined if it exists
        if "const TOTAL_JOBS =" in content:
             content = content.replace("const TOTAL_JOBS =", dedup_logic + "\n        const TOTAL_JOBS =")
             print("Injected deduplication logic before TOTAL_JOBS.")

# 3. Ensure Badge Update on Load
# Look for `window.onload` or script end.
# I'll add a self-executing update at the end of the deduplication logic to be safe.
# Actually, `TOTAL_JOBS` should use `RAW_DATA.length` (the cleaned one).
# If `const TOTAL_JOBS = RAW_DATA.length` exists, it will automatically use the new `RAW_DATA`.

# Let's make sure TOTAL_JOBS uses the new RAW_DATA
if "const TOTAL_JOBS = RAW_DATA.length" not in content:
    # If it was using RAW_DATA_SOURCE (the old name), we need to fix it? 
    # No, the old code used RAW_DATA. Since I redefined RAW_DATA as the cleaned version, 
    # any subsequent code `const TOTAL_JOBS = RAW_DATA.length` will work correctly!
    pass

# We just need to update the static HTML badge text on load because the HTML might say "4076" statically.
# The resetFilters() updates it, but initial load might not.
# I will add a line to update the badge immediately.

update_badge_logic = """
        document.addEventListener('DOMContentLoaded', () => {
            document.getElementById('signal-count').textContent = `${RAW_DATA.length} Aktivních signálů`;
        });
"""
# Append this to the deduplication logic
content = content.replace("console.log(`Data Cleaning: Removed ${RAW_DATA_SOURCE.length - RAW_DATA.length} duplicates. Unique records: ${RAW_DATA.length}`);", 
                          "console.log(`Data Cleaning: Removed ${RAW_DATA_SOURCE.length - RAW_DATA.length} duplicates. Unique records: ${RAW_DATA.length}`);" + update_badge_logic)


with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
