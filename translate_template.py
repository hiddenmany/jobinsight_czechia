#!/usr/bin/env python3
"""Quick script to translate report template to Czech"""

# Translation mapping for the report
translations = {
    # Main headers
    "Benefits & Perks Intelligence": "Benefity & Výhody Intelligence",
    "Work Model Intelligence": "Pracovní Modely Intelligence",
    "Market Signals & Emerging Trends": "Tržní Signály & Vznikající Trendy",
    "Economic Reality & Talent Dynamics": "Ekonomická Realita & Dynamika Talentů",

    # Section titles
    "Most Common Benefits Offered": "Nejčastěji Nabízené Benefity",
    "Average Benefits by Role": "Průměrné Benefity podle Pozice",
    "Work Model by Role (%)": "Pracovní Model podle Pozice (%)",
    "Hot Technologies": "Žhavé Technologie",
    "Active Hiring Companies": "Aktivně Najímající Firmy",
    "Remote/Hybrid Flexibility Reality Check": "Realita Remote/Hybrid Flexibility",
    "Legacy Tech Debt by Role": "Legacy Tech Debt podle Pozice",
    "Contract Types": "Typy Smluv",
    "Tech Stack Gap": "Tech Stack Gap",
    "Top Innovators (Hiring Volume in Modern Stack)": "Top Inovátoři (Objem Náboru v Moderním Stacku)",
    "Role Distribution (Top 5)": "Distribuce Pozic (Top 5)",

    # Table headers
    "Benefit": "Benefit",
    "Percentage": "Procento",
    "Jobs": "Pozice",
    "Role": "Pozice",
    "Avg Benefits Count": "Průměrný Počet Benefitů",
    "Sample Size": "Velikost Vzorku",
    "Technology": "Technologie",
    "Market Share": "Tržní Podíl",
    "Company": "Firma",
    "Active Jobs": "Aktivní Pozice",
    "Legacy %": "Legacy %",
    "Modern %": "Moderní %",
    "Total Jobs": "Celkem Pozic",
    "Title": "Název",
    "Repost Count": "Počet Repostů",
    "Signals": "Signály",
    "Avg. Salary (Est)": "Průměr. Plat (Odhad)",

    # Descriptions and text
    "jobs": "pozic",
    "Hybrid %": "Hybrid %",
    "Office %": "Kancelář %",
    "Remote %": "Remote %",

    # IČO vs HPP section
    "IČO vs HPP Arbitrage": "IČO vs HPP Arbitráž",
    "contractor": "na IČO",
    "employee": "na HPP",
    "median": "medián",
    "sample": "vzorek",
    "premium": "prémie",

    # Talent Pipeline
    "Talent Pipeline Health": "Zdraví Talent Pipeline",
    "Junior:Senior ratio": "Junior:Senior poměr",
    "Assessment": "Hodnocení",
    "Healthy": "Zdravé",

    # AI Washing
    "AI Washing in Non-Tech Roles": "AI Washing v Non-Tech Pozicích",
    "Non-tech roles mentioning AI": "Non-tech pozice zmiňující AI",

    # Ghost Jobs
    "Potential Ghost Jobs": "Potenciální Ghost Jobs",
    "Jobs reposted 3+ times": "Pozice repostované 3x+",
}

# Read the template
with open('C:/Users/phone/Desktop/JobsCzInsight/templates/report_cz.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply translations
for eng, cz in translations.items():
    content = content.replace(eng, cz)

# Write back
with open('C:/Users/phone/Desktop/JobsCzInsight/templates/report_cz.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Translation complete!")
print(f"Applied {len(translations)} translations")
