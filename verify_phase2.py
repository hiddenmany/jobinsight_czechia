from tools.whitelist_discovery import format_report, update_classifiers_file
import tempfile
import os

# Verify report formatting
print("--- Report Format Check ---")
report = format_report({"test": "Tech"}, ["added_term"])
print(report)

# Verify patcher
print("\n--- Patcher Check ---")
# Create dummy file
fd, tmp_path = tempfile.mkstemp(suffix='.py')
with os.fdopen(fd, 'w') as tmp:
    tmp.write("tech_protection = ['a']")
    
try:
    update_classifiers_file(["b"], tmp_path)
    with open(tmp_path, 'r') as f:
        content = f.read()
    print(f"Patched content: {content}")
    assert "'a', 'b'" in content or "'a', \"b\"" in content
    print("Patcher SUCCESS")
finally:
    os.remove(tmp_path)
