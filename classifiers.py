import re

# --- ROLE TAXONOMY ---
ROLE_TAXONOMY = {
    'Developer': ['developer', 'programátor', 'engineer', 'vývojář', 'frontend', 'backend', 
                  'fullstack', 'full-stack', 'web developer', 'mobile developer', 
                  'devops', 'sre', 'platform engineer', 'embedded', 'sysadmin', 'system admin', 'linux admin'],
    'Analyst': ['analyst', 'analytik', 'data analyst', 'business analyst', 'bi analyst', 
                'data scientist', 'data engineer', 'reporting', 'statistik'],
    'Designer': ['designer', 'ux', 'ui', 'grafik', 'product designer', 'visual designer', 
                 'creative', 'art director'],
    'QA': ['tester', 'qa', 'quality', 'test engineer', 'automation', 'sdet'],
    'PM': ['project manager', 'product manager', 'scrum master', 'agile coach', 
           'projektový manažer', 'product owner', 'delivery manager'],
    'Sales': ['obchodní zástupce', 'account manager', 'business development', 'key account', 
              'obchodník', 'sales representative', 'sales manager', 'prodejce aut'],
    'HR': ['recruiter', 'personalist', 'náborář', 'recruitment', 'human resources', 
           'hr business partner', 'hr generalist', 'hr specialist', 'hr manager', 'talent acquisition'],
    'Marketing': ['marketing', 'seo', 'content', 'social media', 'brand', 'growth', 
                  'ppc', 'performance marketing', 'copywriter', 'redaktor', 'editor'],
    'Support': ['support', 'customer', 'helpdesk', 'podpora', 'zákaznick', 'service desk'],
    'Operations': ['operations', 'admin', 'assistant', 'office manager', 'back office', 'koordinátor', 'referent'],
    'Finance': ['accountant', 'účetní', 'finance', 'controller', 'controlling', 'fakturant', 'auditor', 'ekonom'],
    'Management': ['head of', 'director', 'cto', 'ceo', 'vp', 'lead', 'manager', 'vedoucí', 
                   'ředitel', 'team lead', 'tech lead', 'směnový mistr', 'mistr'],
    
    # --- GENERAL MARKET EXPANSION ---
    'Healthcare': ['lékař', 'sestra', 'zdravotní', 'farmaceut', 'psycholog', 'fyzioterapeut', 'doktor', 'ošetřovatel',
                   'zdravotn', 'lékárn', 'sanitář', 'dentist', 'zubní'],
    'Manufacturing': ['dělník', 'operátor výroby', 'montážník', 'svářeč', 'zámečník', 'elektrikář', 'seřizovač',
                      'technolog výroby', 'mistr výroby', 'obráběč', 'cnc', 'výrob', 'provoz', 'linka',
                      'operátor stroj', 'obsluha stroj', 'lisovač', 'lakýrník', 'lakovna', 'nástrojář',
                      'operátor lisy', 'montáž', 'pracovník výroby', 'výrobní dělník', 'směna'],
    'Logistics': ['skladník', 'řidič', 'kurýr', 'logistik', 'zásobovač', 'disponent', 'spediter', 'nákupčí',
                  'sklad', 'doprav', 'přepravn', 'komisař', 'vysokozdvih', 'manipulant', 'expedient',
                  'řidič mhd', 'řidič autobusu', 'řidič kamionu', 'řidič vláček', 'řidička', 'řidiči'],
    'Retail': ['prodavač', 'pokladní', 'prodejce', 'prodejn', 'obchod', 'prodejna', 'market', 'supermarket',
               'vedoucí prodejny', 'store manager', 'cashier', 'retail'],
    'Service': ['číšník', 'kuchař', 'recepční', 'barman', 'uklízeč', 'ostraha', 'security', 'hospodyně',
                'čerpací stanice', 'obsluha', 'údržba', 'technik údržby', 'servis'],
    'Legal': ['právník', 'advokát', 'koncipient', 'paralegal', 'notář', 'compliance'],
    'Construction': ['stavbyvedoucí', 'projektant', 'architekt', 'zedník', 'instalatér', 'malíř'],
    'Education': ['učitel', 'lektor', 'trenér', 'školitel', 'pedagog'],
    
    # --- NEW CATEGORIES TO REDUCE "OTHER" BUCKET ---
    'Social Services': ['sociální pracovník', 'sociální služb', 'týdenní teta', 'týdenní strýc', 
                        'doprovázející', 'pečovatel', 'asisten', 'pracovník v sociálních'],
    'Hospitality': ['pokojská', 'housekeeper', 'hotel', 'mcdonald', 'mcdonalds', 'barista', 
                    'obsluha čerpací', 'čerpací stanice', 'fast food', 'restaurace'],
    'Technical Specialists': ['technolog', 'metrolog', 'laboratorn', 'měření', '3d měření', 
                              'lab technik', 'chemik', 'fyzik', 'specialista technické'],
    'Electromechanics': ['elektromechanik', 'nástrojář', 'mechanik', 'elektrotechnik', 
                         'údržbář', 'servisní technik', 'preparing', 'přípravář']
}

# --- SENIORITY PATTERNS ---
SENIORITY_PATTERNS = {
    'Junior': ['junior', 'entry', 'trainee', 'intern', 'graduate', 'absolvent', 
               '0-2 let', '1-2 roky', 'začátečník', 'entry-level'],
    'Mid': ['mid', 'regular', '2-5 let', '3-5 let', '2+ let', 'medior'],
    'Senior': ['senior', 'experienced', 'sr.', '5+ let', '5-10 let', 'zkušený', 
               'pokročilý', 'specialist'],
    'Lead': ['lead', 'principal', 'staff', 'architect', 'tech lead', 'team lead', 
             'vedoucí týmu', 'chapter lead'],
    'Executive': ['head of', 'director', 'vp', 'chief', 'cto', 'ceo', 'cfo', 'coo',
                  'ředitel', 'c-level', 'executive']
}

class JobClassifier:
    @staticmethod
    def classify_role(title: str, description: str = "") -> str:
        """Classify job into role category based on title and description.

        FIXED: Added compound phrase handling and negative context checks.
        """
        text = f"{title} {description}".lower()
        title_lower = title.lower()

        # Pre-checks for compound phrases that could match multiple categories
        # FIXED: Handle QA/Test Engineer before 'engineer' matches Developer
        if 'qa' in title_lower or 'quality assurance' in title_lower:
            # But exclude non-tech quality roles
            non_tech_quality = ['food', 'manufacturing', 'iso', 'výrob', 'produk',
                               'fabric', 'factory', 'plant', 'automotive', 'potravina']
            if not any(kw in text for kw in non_tech_quality):
                return 'QA'

        if 'test engineer' in title_lower or 'tester' in title_lower:
            # Software testing context
            if 'software' in text or 'automation' in text or 'qa' in text:
                return 'QA'

        # Helper function for smart matching (avoids Czech substring false positives)
        def smart_match(text: str, keyword: str) -> bool:
            # For short keywords that are common substrings, use word boundaries
            if keyword in ['hr', 'it', 'pr', 'ui', 'ux', 'grafik', 'qa']:
                # Check if keyword appears as separate word or in compound like "hr-manager"
                pattern = r'\b' + re.escape(keyword) + r'(?:\b|[-_])'
                return bool(re.search(pattern, text))
            else:
                # For longer keywords, simple substring match is fine
                return keyword in text

        # Priority: Check title first (more accurate), then description
        matched_role = None
        for role, keywords in ROLE_TAXONOMY.items():
            if any(smart_match(title_lower, kw) for kw in keywords):
                matched_role = role
                break

        # If not matched in title, check description
        if not matched_role:
            for role, keywords in ROLE_TAXONOMY.items():
                if any(smart_match(text, kw) for kw in keywords):
                    matched_role = role
                    break

        # FIXED: Negative context checks for false positives
        # 1. "Grafik směn" (shift schedule) should NOT be Designer
        if matched_role == 'Designer':
            shift_indicators = ['směn', 'rozvrh', 'schedule', 'plánování směn']
            if any(indicator in text for indicator in shift_indicators):
                matched_role = None  # Continue to fallback

        # 2. "Quality" in non-tech context should NOT be QA
        if matched_role == 'QA':
            non_tech_quality = ['food', 'manufacturing', 'iso', 'výrob', 'produk',
                               'fabric', 'factory', 'plant', 'automotive', 'potravina']
            if any(kw in text for kw in non_tech_quality):
                matched_role = 'Manufacturing'  # More appropriate category

        # Downgrade low-level "Management" or Tech-focused leads to actual role category
        if matched_role == 'Management':
            # 1. Check for Tech Lead / Engineering Lead (should be Developer)
            tech_indicators = ['tech', 'software', 'engineer', 'development', 'it ', 'vývoj', 'programátor']
            if any(indicator in title_lower for indicator in tech_indicators):
                return 'Developer'

            # 2. Check for shift leader / store manager patterns (not true executives)
            low_wage_indicators = [
                'směnový', 'vedoucí směny', 'vedoucí prodejny', 'store manager',
                'team leader výroby', 'mistr výroby', 'vedoucí skladu', 'vedoucí restaurace',
                'shift leader', 'shift supervisor'
            ]
            if any(indicator in title_lower for indicator in low_wage_indicators):
                # Reclassify based on context
                if any(kw in text for kw in ['sklad', 'logistik', 'warehouse']):
                    return 'Logistics'
                elif any(kw in text for kw in ['výrob', 'provoz', 'směn', 'production', 'factory']):
                    return 'Manufacturing'
                elif any(kw in text for kw in ['prodej', 'obchod', 'market', 'store', 'shop']):
                    return 'Retail'
                elif any(kw in text for kw in ['restaurace', 'kuchyň', 'hotel', 'restaurant', 'kitchen', 'service']):
                    return 'Service'

        # Executive downgrading logic (User request) -> Mid/Junior if retail/sales without C-level keywords
        # "Sales Executive", "Account Executive" -> Mid (standard industry title inflation)
        if 'executive' in title_lower and not any(x in title_lower for x in ['head', 'director', 'chief', 'c-level', 'vp', 'president', 'ředitel']):
             return 'Sales' if 'sales' in title_lower or 'account' in title_lower else 'Mid'

        return matched_role if matched_role else 'Other'

    @staticmethod
    def detect_seniority(title: str, description: str = "") -> str:
        """Detect seniority level from title and description.

        FIXED: Now prioritizes title over description to avoid false positives
        like "Developer at Senior Solutions Inc." being classified as Senior.
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""

        # Priority order: Executive > Lead > Senior > Junior > Mid (default)
        priority_order = ['Executive', 'Lead', 'Senior', 'Junior', 'Mid']

        # First pass: Check title only (most reliable)
        for level in priority_order:
            patterns = SENIORITY_PATTERNS[level]
            if any(p in title_lower for p in patterns):
                return level

        # Second pass: Check description only if not found in title
        for level in priority_order:
            patterns = SENIORITY_PATTERNS[level]
            if any(p in desc_lower for p in patterns):
                return level

        return 'Mid'  # Default to Mid if unclear
