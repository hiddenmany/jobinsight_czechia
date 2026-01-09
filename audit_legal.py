import duckdb
import os
from settings import settings

DB_PATH = str(settings.get_db_path())
OUTPUT_FILE = "LEGAL_AUDIT_REPORT.md"

# --- LEGAL DEFINITIONS (Based on Zakonik_Prace_Raw_Fetch.txt) ---
# § 1a, § 16: Prohibition of Discrimination
DISCRIMINATION_PATTERNS = {
    "Gender Bias (Female explicit)": [
        r"\bhledáme\s+asistentku\b", r"\bhledáme\s+uklízečku\b", r"\bhledáme\s+recepční\b",
        r"\bhledáme\s+hostesku\b", r"\bhledáme\s+prodavačku\b", r"\bhledáme\s+sestru\b",
        r"\bžena\b", r"\bženu\b"
    ],
    "Gender Bias (Male explicit)": [
        r"\bhledáme\s+dělníka\b", r"\bhledáme\s+skladníka\b", r"\bhledáme\s+řidiče\b",
        r"\bhledáme\s+programátora\b", r"\bmuž\b", r"\bmuže\b"
    ],
    "Age Bias": [
        r"\bmladý\s+kolektiv\b", r"\bmladý\s+tým\b", r"\bvěk\s+do\b", 
        r"\bjuniorní\s+věk\b", r"\bdůchodce\b"
    ],
    "Family Status": [
        r"\bbezdětnou\b", r"\bbez\s+dětí\b", r"\bsvobodnou\b"
    ]
}

# § 2, § 3: Dependent Work vs Švarcsystém (Illegal Employment)
# "Závislá práce může být vykonávána výlučně v základním pracovněprávním vztahu"
SVARCSYSTEM_INDICATORS = {
    "Contract Type": [r"\bičo\b", r"\bživnost\b", r"\bfakturace\b", r"\bžl\b"],
    "Dependent Features": [
        r"\bfixní\s+pracovní\s+doba\b", r"\b9-17\b", r"\b8-16\b", 
        r"\bpovinná\s+přítomnost\b", r"\bkancelář\b", r"\bna\s+pracovišti\b",
        r"\bfiremní\s+notebook\b", r"\bfiremní\s+telefon\b", # Equipment provided by employer
        r"\bdovolená\b", r"\bplacené\s+volno\b", # Vacation (employee benefit)
        r"\bsick\s+days\b", r"\bstravenky\b"
    ]
}

def analyze_discrimination(text):
    text = text.lower()
    found = []
    for category, patterns in DISCRIMINATION_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                # Context check: ignore "vhodné pro důchodce" (legal) vs "hledáme důchodce" (gray area)
                if "důchodce" in pat and "vhodné" in text:
                    continue
                found.append(f"{category}: '{pat.replace(r'\\b', '').strip()}'")
                break # One hit per category is enough
    return found

def analyze_svarcsystem(text):
    text = text.lower()
    
    # 1. Check for Contractor keywords
    is_contractor = False
    contract_kw = []
    for pat in SVARCSYSTEM_INDICATORS["Contract Type"]:
        if re.search(pat, text):
            is_contractor = True
            contract_kw.append(pat.replace(r'\\b', ''))
    
    if not is_contractor:
        return []
    
    # 2. If Contractor, check for Employee characteristics (Dependent Work)
    dependent_features = []
    for pat in SVARCSYSTEM_INDICATORS["Dependent Features"]:
        if re.search(pat, text):
            dependent_features.append(pat.replace(r'\\b', ''))
            
    if dependent_features:
        return [f"Potential Švarcsystém (§ 2, § 3): IČO combined with {', '.join(dependent_features)}"]
    
    return []

def run_audit():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("SELECT title, company, description, link, source FROM signals").df()
    con.close()
    
    print(f"Auditing {len(df)} job descriptions against Labour Law (262/2006 Sb.)...")
    
    violations = []
    
    for _, row in df.iterrows():
        title = row['title']
        desc = row['description'] or ""
        text = f"{title} {desc}"
        
        # Check Discrimination
        discrim_issues = analyze_discrimination(text)
        
        # Check Švarcsystém
        svarc_issues = analyze_svarcsystem(text)
        
        issues = discrim_issues + svarc_issues
        
        if issues:
            violations.append({
                "Company": row['company'],
                "Title": title,
                "Link": row['link'],
                "Issues": issues
            })
    
    # Generate Report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# ⚖️ LABOUR LAW COMPLIANCE AUDIT\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"**Scanned:** {len(df)} job listings\n")
        f.write(f"**Legal Grounding:** Zákoník práce (262/2006 Sb.) - § 1a, § 2, § 3, § 16\n\n")
        
        f.write("## 🚨 Executive Summary\n")
        f.write(f"- **Total Flagged Listings:** {len(violations)} ({len(violations)/len(df)*100:.1f}%)\n")
        
        # Stats by type
        discrim_count = sum(1 for v in violations if any("Bias" in i for i in v['Issues']))
        svarc_count = sum(1 for v in violations if any("Švarcsystém" in i for i in v['Issues']))
        
        f.write(f"- **Potential Discrimination (§ 16):** {discrim_count}\n")
        f.write(f"- **Potential Švarcsystém (§ 2, § 3):** {svarc_count}\n\n")
        
        f.write("## 📝 Detailed Findings\n\n")
        
        if not violations:
            f.write("No obvious violations found based on current keywords.\n")
        
        for v in violations[:100]: # Limit to top 100 to avoid huge file
            f.write(f"### {v['Title']} ({v['Company']})\n")
            f.write(f"**Link:** {v['Link']}\n")
            f.write("**Flags:**\n")
            for issue in v['Issues']:
                f.write(f"- ⚠️ {issue}\n")
            f.write("\n---\n")

    print(f"Audit complete. Report saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_audit()
