import re

# --- ROLE TAXONOMY ---
ROLE_TAXONOMY = {
    'Legal': ['právník', 'advokát', 'koncipient', 'paralegal', 'notář', 'compliance', 'lawyer'],
    'Healthcare': ['lékař', 'sestra', 'zdravotní', 'farmaceut', 'psycholog', 'fyzioterapeut', 'doktor', 'ošetřovatel',
                   'zdravotn', 'lékárn', 'sanitář', 'dentist', 'zubní', 'biomedic', 'nurse', 'chirurg', 'terapeut', 'radiolog', 'optometrista', 'adiktolog'],
    'Developer': ['developer', 'programátor', 'software engineer', 'vývojář', 'frontend', 'backend', 
                  'fullstack', 'full-stack', 'web developer', 'mobile developer', 
                  'devops', 'sre', 'platform engineer', 'embedded', 'sysadmin', 'system admin', 'linux admin',
                  'it manažer', 'salesforce', 'abap', 'firmware', 'net developer', 'java developer',
                  'it administrator', 'it administrátor', 'database administrator', 'databázový administrátor', 'helpdesk',
                  'software inženýr', 'sw inženýr', 'sw engineer', 'it inženýr', 'principal engineer', 'staff engineer'],
    # NEW: General Engineering (non-IT) - HVAC, electrical, mechanical, civil
    'General Engineering': ['hvac', 'vzduchotechnik', 'klimatizace', 'topení', 'vytápění', 'chlazení',
                           'electrical engineer', 'elektro inženýr', 'silnoproud', 'slaboproud',
                           'elektroprojektant', 'strojní projektant',
                           'mechanical engineer', 'strojní inženýr', 'strojírenský inženýr',
                           'civil engineer', 'stavební inženýr', 'konstruktér', 'konstrukční inženýr',
                           'projekční inženýr', 'projekční technik', 'projektový inženýr',
                           'field engineer', 'application engineer',
                           'tester hardware', 'hw engineer', 'hardware engineer',
                           'plc programmer', 'plc programátor', 'automation engineer', 'automatizac',
                           'technický inženýr', 'commissioning engineer', 'validation engineer', 'reliability engineer'],
    'QA': ['tester', 'qa', 'quality', 'test engineer', 'sdet'],
    'Analyst': ['analyst', 'analytik', 'data analyst', 'business analyst', 'bi analyst', 
                'data scientist', 'data engineer', 'reporting', 'statistik'],
    'Finance': ['accountant', 'účetní', 'finance', 'controller', 'controlling', 'fakturant', 'auditor', 'ekonom', 'bankéř', 'banker', 'bankovní poradce',
                'accounts payable', 'accounts receivable', 'mzdová účetní', 'payroll', 'daňový poradce', 'daňová', 'likvidátor škod', 'hypotéč'],
    'HR': ['recruiter', 'personalist', 'náborář', 'recruitment', 'human resources', 
           'hr business partner', 'hr generalist', 'hr specialist', 'hr manager', 'talent acquisition', 'people development'],
    'PM': ['project manager', 'product manager', 'scrum master', 'agile coach', 
           'projektový manažer', 'product owner', 'delivery manager'],
    'Sales': ['obchodní zástupce', 'account manager', 'business development', 'key account', 
              'obchodník', 'sales representative', 'sales manager', 'prodejce aut',
              'sales', 'prodej', 'channel development', 'partner development', 'sales engineer', 'obchodní', 'account executive', 'telesales'],
    'Marketing': ['marketing', 'seo', 'content', 'social media', 'brand', 'growth', 
                  'ppc', 'performance marketing', 'copywriter', 'redaktor', 'editor',
                  'hosteska', 'promotér', 'pr executive', 'event manažer', 'event coordinator', 'produkční'],
    'Hospitality': ['pokojská', 'housekeeper', 'hotel', 'mcdonald', 'mcdonalds', 'barista',
                    'obsluha čerpací', 'čerpací stanice', 'fast food', 'restaurace', 'restaurant', 'kuchař', 'číšník', 'barman', 'boulevard', 'kfc', 'burger king'],
    'Retail': ['prodavač', 'pokladní', 'prodejce', 'prodejn', 'obchod', 'prodejna', 'market', 'supermarket',
               'vedoucí prodejny', 'store manager', 'cashier', 'retail', 'florist'],
    'Education': ['učitel', 'lektor', 'trenér', 'školitel', 'pedagog', 'phd', 'postdoc', 'akademický', 'didaktik', 'vychovatel', 'docent', 'knihovník', 'škola', 'školka'],
    'Logistics': ['skladník', 'řidič', 'kurýr', 'logistik', 'zásobovač', 'disponent', 'spediter', 'nákupčí',
                  'sklad', 'doprav', 'přepravn', 'komisař', 'vysokozdvih', 'manipulant', 'expedient',
                  'řidič mhd', 'řidič autobusu', 'řidič kamionu', 'řidič vláček', 'řidička', 'řidiči',
                  'dispečer', 'celní', 'warehouse'],
    'Manufacturing': ['dělník', 'operátor výroby', 'montážník', 'svářeč', 'zámečník', 'elektrikář', 'seřizovač',
                      'technolog výroby', 'mistr výroby', 'obráběč', 'cnc', 'výrob', 'výrobní', 'provozní', 'linka',
                      'operátor stroj', 'obsluha stroj', 'lisovač', 'lakýrník', 'lakovna', 'nástrojář',
                      'operátor lisy', 'montáž', 'pracovník výroby', 'výrobní dělník', 'směna', 'industrial engineer',
                      'process engineer', 'procesní inženýr', 'quality engineer', 'commissioning engineer', 'technolog', 'horizontkář', 'strojník', 'jeřábník', 'klempíř'],
    'Construction': ['stavbyvedoucí', 'projektant', 'architekt', 'zedník', 'instalatér', 'malíř', 'statik', 'structural engineer', 'geodet', 'geolog', 'přípravář', 'rozpočtář', 'stavba'],
    'Designer': ['designer', 'ux', 'ui', 'grafik', 'product designer', 'visual designer', 
                 'creative', 'art director'],
    'Social Services': ['sociální pracovník', 'sociální služb', 'týdenní teta', 'týdenní strýc', 
                        'doprovázející', 'pečovatel', 'asisten', 'pracovník v sociálních', 'pečující', 'chůva', 'mentor'],
    'Technical Specialists': ['metrolog', 'laboratorn', 'měření', '3d měření',
                              'lab technik', 'chemik', 'fyzik', 'specialista technické', 'laborant', 'ekolog', 'biolog', 'revizní technik', 'zkušební technik'],
    'Electromechanics': ['elektromechanik', 'nástrojář', 'mechanik', 'elektrotechnik',
                         'údržbář', 'servisní technik', 'analog design', 'elektronik'],
    'Support': ['support', 'customer', 'helpdesk', 'podpora', 'zákaznick', 'service desk', 'incident manager', 'call centrum', 'call center', 'péče o klienty', 'zákaznická linka'],
    'Operations': ['operations', 'admin', 'assistant', 'office manager', 'back office', 'koordinátor', 'referent',
                   'asistent', 'recepční', 'executive assistant', 'administrativ'],
    'Service': ['uklízeč', 'ostraha', 'security', 'hospodyně', 'obsluha', 'údržba', 'technik údržby', 'servis', 'údržbář', 'hotelový technik', 'strážný', 'zahradník', 'vrátný', 'policista', 'hasič', 'záchranář', 'plavčík', 'čistič'],
    'Management': ['head of', 'director', 'cto', 'ceo', 'vp', 'lead', 'manager', 'vedoucí', 
                   'ředitel', 'team lead', 'tech lead', 'směnový mistr', 'mistr']
}

# --- SENIORITY PATTERNS ---
SENIORITY_PATTERNS = {
    'Junior': ['junior', 'entry', 'trainee', 'intern', 'graduate', 'absolvent',
               '0-2 let', '1-2 roky', 'začátečník', 'entry-level', 'praktikant'],
    'Mid': ['mid', 'regular', '2-5 let', '3-5 let', '2+ let', 'medior'],
    'Senior': ['senior', 'experienced', 'sr.', '5+ let', '5-10 let', 'zkušený',
               'pokročilý', 'specialist'],
    'Lead': ['lead', 'principal', 'staff', 'architect', 'tech lead', 'team lead',
             'vedoucí týmu', 'chapter lead'],
    'Executive': ['head of', 'director', 'vp', 'chief', 'cto', 'ceo', 'cfo', 'coo',
                  'ředitel', 'c-level', 'executive']
}

try:
    from embedding_classifier import EmbeddingClassifier, EMBEDDINGS_AVAILABLE
    _USE_EMBEDDINGS = EMBEDDINGS_AVAILABLE
except ImportError:
    _USE_EMBEDDINGS = False
    EmbeddingClassifier = None


class JobClassifier:
    """
    Hybrid job classifier using ML embeddings with keyword fallback.
    """

    # Class-level flag to force keyword mode (useful for debugging/testing)
    USE_EMBEDDINGS = _USE_EMBEDDINGS

    @staticmethod
    def get_classification_mode() -> str:
        """Return current classification mode for debugging."""
        if JobClassifier.USE_EMBEDDINGS and EmbeddingClassifier and EmbeddingClassifier.is_available():
            return "ML_EMBEDDINGS"
        return "KEYWORD_MATCHING"

    @staticmethod
    def classify_role(title: str, description: str = "") -> str:
        """Classify job into role category using hybrid approach."""
        keyword_result = JobClassifier._classify_role_keywords(title, description)
        if keyword_result != "Other":
            return keyword_result

        if JobClassifier.USE_EMBEDDINGS and EmbeddingClassifier:
            try:
                ml_result = EmbeddingClassifier.classify_role(title, description)
                if ml_result is not None and ml_result != "Other":
                    return ml_result
            except Exception:
                pass

        return "Other"

    @staticmethod
    def _classify_role_keywords(title: str, description: str = "") -> str:
        """Keyword-based role classification."""
        text = f"{title} {description}".lower()
        title_lower = title.lower()

        def smart_match(text: str, keyword: str) -> bool:
            # Keywords that REQUIRE word boundaries to avoid false positives (e.g., 'controller' in 'controllers')
            boundary_keywords = [
                'hr', 'it', 'pr', 'ui', 'ux', 'grafik', 'qa', 'sales', 
                'controller', 'lead', 'manager', 'director', 'vp', 'ceo', 'cto',
                'pokojská', 'školka', 'banker', 'bankéř', 'účetní'
            ]
            if keyword in boundary_keywords:
                # Special exclusion for 'grafik směn'/'grafik rozvrhu' (Shift Scheduler)
                if keyword == 'grafik' and ('grafik směn' in text or 'grafik rozvrhu' in text):
                    return False
                pattern = r'\b' + re.escape(keyword) + r'(?:\b|[-_])'
                return bool(re.search(pattern, text))
            else:
                return keyword in text

        # 1. TOP-LEVEL OVERRIDES (The "Fast Path")
        # Hospitality (Brands & Specific roles)
        if any(kw in title_lower for kw in ['mcdonald', 'burger king', 'fast food', 'restaurace', 'restaurant', 'kuchař', 'číšník', 'barman', 'boulevard', 'kfc', 'bageterie']):
             return 'Hospitality'
        # Education / Research
        if any(kw in title_lower for kw in ['phd', 'ph.d.', 'postdoc', 'akademický', 'docent', 'didaktik', 'pedagog', 'učitel', 'lektor']):
             return 'Education'
        # Legal
        if any(kw in title_lower for kw in ['právník', 'advokát', 'legal', 'compliance', 'notář']):
             return 'Legal'
        # Healthcare
        if any(kw in title_lower for kw in ['chirurg', 'lékař', 'sestra', 'doktor', 'radiolog', 'terapeut', 'zubní', 'farmaceut', 'optometrista', 'adiktolog']):
             return 'Healthcare'
        # Sales
        if any(kw in title_lower for kw in ['business development', 'channel development', 'sales engineer', 'account executive', 'obchodník', 'obchodní zástupce', 'telesales']):
             return 'Sales'
        # Service (Physical Security/Safety)
        if any(kw in title_lower for kw in ['policista', 'hasič', 'ostraha', 'strážný', 'security', 'vrátný', 'plavčík', 'záchranář']):
             return 'Service'

        # 2. MATCHING LOOP
        matched_role = None
        # Priority: Specific roles first
        priority_order = ['Developer', 'Analyst', 'QA', 'PM', 'Designer', 'Legal', 'Healthcare', 'Finance', 'HR', 'General Engineering', 'Manufacturing', 'Construction', 'Retail', 'Hospitality', 'Logistics', 'Marketing', 'Education', 'Social Services', 'Technical Specialists', 'Electromechanics', 'Support', 'Operations', 'Service', 'Management']
        
        for role in priority_order:
            keywords = ROLE_TAXONOMY.get(role, [])
            if any(smart_match(title_lower, kw) for kw in keywords):
                matched_role = role
                break

        if not matched_role:
            for role in priority_order:
                keywords = ROLE_TAXONOMY.get(role, [])
                if any(smart_match(text, kw) for kw in keywords):
                    matched_role = role
                    break

        # ---------------------------------------------------------
        # POST-CLASSIFICATION REFINEMENT (The "Sanity Check" Layer)
        # ---------------------------------------------------------

        # A. Tech Integrity
        if matched_role in ['Developer', 'Analyst', 'QA', 'PM', 'Designer']:
             it_protection = ['software', 'firmware', 'embedded', 'sw ', 'development', 'vývoj', 
                                'programátor', 'data', 'cloud', 'devops', 'python', 'java', 'sql', 'api',
                                'web ', 'frontend', 'backend', 'fullstack', 'mobile', 'ios', 'android']
             
             # If it's labeled as IT but has strong Engineering/Manufacturing indicators and lacks IT indicators
             eng_indicators = ['industrial', 'process', 'manufacturing', 'production', 'výrob', 'stroj', 'mechanical', 'electrical', 'elektro', 'hvac', 'plc', 'scada', 'automatizace']
             if any(kw in title_lower for kw in eng_indicators) and not any(kw in title_lower for kw in it_protection):
                  if 'automation' in title_lower or 'plc' in title_lower or 'automatizace' in title_lower:
                       return 'General Engineering'
                  if any(kw in title_lower for kw in ['process', 'industrial', 'výrob', 'procesní']):
                       return 'Manufacturing'
                  return 'General Engineering'

             tech_protection = it_protection + ['technik', 'inženýr', 'engineer', 'sap', 'automatizace']
             if any(kw in text for kw in tech_protection):
                  return matched_role
             
             if matched_role == 'Developer' and ('developersk' in text or 'nemovitost' in text):
                  return 'Construction'
             if any(kw in title_lower for kw in ['administrator', 'administrátor']) and 'it' in title_lower:
                  return 'Developer'
             # Allow fall-through to specific cleanup blocks
             pass

        # 1. Developer Clean-up (Enhanced: route non-IT engineering to correct categories)
        if matched_role == 'Developer':
            # HVAC/MEP engineering keywords - route to General Engineering
            hvac_mep_keywords = [
                'hvac', 'vzduchotechnik', 'klimatizace', 'topení', 'vytápění', 'chlazení',
                'silnoproud', 'slaboproud', 'tze', 'technické zařízení budov', 'mep'
            ]
            if any(kw in title_lower or kw in text for kw in hvac_mep_keywords):
                return 'General Engineering'
            
            # General non-IT engineering keywords
            non_it_keywords = [
                'industrial', 'process', 'quality', 'sales', 'quotation', 'structural', 'civil',
                'mechanical', 'electrical', 'výrob', 'technolog', 'statik', 'projektant',
                'commissioning', 'service', 'maintenance', 'údržba', 'servis', 'hardware', 'hw ',
                'elektro', 'geodet', 'geolog', 'biomedic', 'sestra', 'zdravotní', 'laborant',
                'horizontkář', 'analog', 'asistent', 'cad', 'inžernýr', 'strojní', 'strojírenský',
                'konstruktér', 'konstrukční', 'validation', 'reliability'
            ]
            if any(kw in title_lower for kw in non_it_keywords):
                # Preserve QA/Sales routing
                if 'quality' in title_lower and 'software' not in text: return 'QA'
                if 'sales' in title_lower: return 'Sales'
                
                # Only reclassify if NOT clearly IT
                it_protection = ['software', 'firmware', 'embedded', 'sw ', 'development', 'vývoj', 
                                'programátor', 'data', 'cloud', 'devops', 'python', 'java', 'sql', 'api']
                if not any(kw in text for kw in it_protection):
                    # Route to General Engineering for engineering-specific roles
                    if any(kw in title_lower for kw in ['mechanical', 'strojní', 'strojírenský', 'konstruktér', 'konstrukční']):
                        return 'General Engineering'
                    if any(kw in title_lower for kw in ['electrical', 'elektro', 'silnoproud', 'slaboproud']):
                        return 'General Engineering'
                    if any(kw in title_lower for kw in ['industrial', 'process', 'výrob', 'procesní']):
                        return 'Manufacturing'
                    if any(kw in title_lower for kw in ['structural', 'civil', 'statik', 'projektant', 'stavební']):
                        return 'Construction'
                    if any(kw in title_lower for kw in ['quality', 'validation', 'reliability']) and 'engineer' in title_lower:
                        return 'General Engineering'
                    if 'laborant' in title_lower: return 'Technical Specialists'
                    if 'biomedic' in title_lower or 'sestra' in title_lower: return 'Healthcare'
                    return 'Manufacturing'


        # 1.5 QA Clean-up

        if matched_role == 'QA':
            # Route non-IT quality roles to Manufacturing/General Engineering
            non_it_quality = ['manufacturing', 'production', 'výrob', 'stroj', 'mechanical', 'construction', 'stavb', 'food', 'potravin', 'control', 'iso']
            if any(kw in text for kw in non_it_quality) and 'software' not in text and 'automation' not in text:
                if 'engineer' in title_lower or 'inženýr' in title_lower:
                    return 'General Engineering'
                return 'Manufacturing'

        # 2. Healthcare Clean-up
        if matched_role == 'Healthcare':
             if any(kw in text for kw in ['průkaz', 'potravinář', 'uklid', 'úklid', 'zahradník', 'ostraha', 'security']):
                  if not any(kw in title_lower for kw in ['lékař', 'sestra', 'biomedic', 'farmaceut', 'chirurg', 'optometr', 'adiktolog']):
                       return 'Service'

        # 3. Operations Clean-up
        if matched_role == 'Operations':
             if 'knihovník' in title_lower: return 'Education'
             if 'radiolog' in title_lower or 'zubní' in title_lower: return 'Healthcare'
             if any(kw in title_lower for kw in ['sociální', 'pečovatel', 'chůva', 'mentor']): return 'Social Services'
             if any(kw in title_lower for kw in ['úklid', 'čištění', 'vrátný', 'ostraha']): return 'Service'
             if any(kw in title_lower for kw in ['staveb', 'projekt', 'geodet']) and 'asistent' in title_lower: return 'Construction'

        if matched_role == 'Management':
            # Tech Lead / Team Lead / IT Manager in IT context -> Developer
            if ('tech lead' in title_lower or 'team lead' in title_lower or 'it manager' in title_lower) and any(kw in text for kw in ['software', 'python', 'java', 'react', 'node', 'aws', 'cloud', 'developer', 'engineer']):
                 return 'Developer'

            if any(kw in title_lower for kw in ['store', 'prodejn', 'směn', 'shift', 'restaurace', 'restaurant', 'hotel', 'sklad', 'warehouse']):
                 # Check full text for warehouse context (e.g. Shift Leader in Amazon Warehouse)
                 if 'sklad' in text or 'warehouse' in text: return 'Logistics'
                 if 'store' in title_lower or 'prodejn' in title_lower: return 'Retail'
                 if 'restaurace' in title_lower or 'hotel' in title_lower: return 'Hospitality'
                 if 'směn' in title_lower or 'shift' in title_lower: return 'Manufacturing'
            if 'developersk' in text or 'real estate' in text: return 'Construction'

        # 5. Marketing Clean-up
        if matched_role == 'Marketing':
             if 'payable' in text or 'receivable' in text or 'faktura' in text: return 'Finance'
             if 'it' in title_lower and any(kw in title_lower for kw in ['audit', 'licence', 'specialista']): return 'Developer'

        # 6. Finance Clean-up
        if matched_role == 'Finance':
             if 'knihovník' in title_lower: return 'Education'

        return matched_role if matched_role else 'Other'

    @staticmethod
    def detect_seniority(title: str, description: str = "") -> str:
        """Detect seniority level."""
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        priority_order = ['Executive', 'Lead', 'Senior', 'Junior', 'Mid']
        non_executive_mgmt = ['vedoucí', 'mistr', 'směnový', 'store manager', 'vedoucí prodejny',
                              'vedoucí skladu', 'vedoucí směny', 'shift']
        is_non_exec_mgmt = any(term in title_lower for term in non_executive_mgmt)
        for level in priority_order:
            patterns = SENIORITY_PATTERNS[level]
            if any(p in title_lower for p in patterns):
                if level == 'Executive' and is_non_exec_mgmt: return 'Lead'
                return level
        for level in priority_order:
            if level == 'Executive': continue
            patterns = SENIORITY_PATTERNS[level]
            if any(p in desc_lower for p in patterns): return level
        return 'Mid'
