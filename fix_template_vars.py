#!/usr/bin/env python3
"""Fix broken variable names in Czech template"""

# Variable name fixes (Czech -> English)
fixes = {
    'total_pozic': 'total_jobs',
    'tech_prémie': 'tech_premium',
    'seniority_prémie': 'seniority_premium',
    'skill_prémies': 'skill_premiums',
    'remote_prémie': 'remote_premium',
    'medán': 'median',
    'pozic': 'jobs',  # Only in variable names, not user text
    '.prémie': '.premium',  # For object properties
    '.Pozice': '.Jobs',  # For dict keys
    '.Procento': '.Percentage',  # For dict keys
    '.Technologie': '.Technology',  # For dict keys
    'Tržní Podíl': 'Market Share',  # For dict keys
    '.Firma': '.Company',
    '.Název': '.Title',
    'Počet Repostů': 'Repost Count',
    'Active Pozice': 'Active Jobs',  # For dict keys
    'Total Pozice': 'Total Jobs',  # For dict keys
    'Moderní': 'Modern',  # When in dict key context like role['Moderní %']
    'Signály': 'Signals',  # For dict keys
    'Průměr. Plat (Odhad)': 'Avg. Salary (Est)',  # For dict keys
    'prémie-positive': 'premium-positive',  # CSS class
    'prémie-negative': 'premium-negative',  # CSS class
    'ghost_pozic': 'ghost_jobs',
    'ghostPoziceSection': 'ghostJobsSection',
    'ghostPoziceToggle': 'ghostJobsToggle',
    'ico_medán': 'ico_median',
    'hpp_medán': 'hpp_median',
    'english_medán': 'english_median',
    'czech_medán': 'czech_median',
    'remote_medán': 'remote_median',
    'office_medán': 'office_median',
    'medán_salary': 'median_salary',
}

# Read file
with open('C:/Users/phone/Desktop/JobsCzInsight/templates/report_cz.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Apply fixes
for bad, good in fixes.items():
    content = content.replace(bad, good)

# Write back
with open('C:/Users/phone/Desktop/JobsCzInsight/templates/report_cz.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed variable names!")
