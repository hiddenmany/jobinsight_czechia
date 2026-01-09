import re

ROLE_TAXONOMY = {
    'Developer': ['developer', 'programĂˇtor', 'engineer', 'vĂ˝vojĂˇĹ™', 'frontend', 'backend', 
                  'fullstack', 'full-stack', 'web developer', 'mobile developer', 
                  'devops', 'sre', 'platform engineer', 'embedded', 'sysadmin', 'system admin', 'linux admin',
                  'inĹľenĂ˝r', 'it manaĹľer'],
}

def smart_match(text: str, keyword: str) -> bool:
    if keyword in ['hr', 'it', 'pr', 'ui', 'ux', 'grafik', 'qa']:
        pattern = r'\b' + re.escape(keyword) + r'(?:\b|[-_])'
        return bool(re.search(pattern, text))
    else:
        return keyword in text

title = "Channel Development Manager - HoReCa segment"
title_lower = title.lower()
text = title_lower

print(f"Testing title: '{title}'")

for role, keywords in ROLE_TAXONOMY.items():
    for kw in keywords:
        if smart_match(title_lower, kw):
            print(f"MATCHED: Role '{role}' with keyword '{kw}'")
