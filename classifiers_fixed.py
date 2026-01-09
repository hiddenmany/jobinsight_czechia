import re

# --- ROLE TAXONOMY ---
ROLE_TAXONOMY = {
    'Developer': ['developer', 'programátor', 'engineer', 'vývojář', 'frontend', 'backend', 
                  'fullstack', 'full-stack', 'web developer', 'mobile developer', 
                  'devops', 'sre', 'platform engineer', 'embedded', 'sysadmin', 'system admin', 'linux admin',
                  'inženýr', 'it manažer', 'salesforce', 'abap'],
    'Analyst': ['analyst', 'analytik', 'data analyst', 'business analyst', 'bi analyst', 
                'data scientist', 'data engineer', 'reporting', 'statistik'],
    'Designer': ['designer', 'ux', 'ui', 'grafik', 'product designer', 'visual designer', 
                 'creative', 'art director'],
    'QA': ['tester', 'qa', 'quality', 'test engineer', 'automation', 'sdet'],
    'PM': ['project manager', 'product manager', 'scrum master', 'agile coach', 
           'projektový manažer', 'product owner', 'delivery manager'],
    'Sales': ['obchodní zástupce', 'account manager', 'business development', 'key account', 
              'obchodník', 'sales representative', 'sales manager', 'prodejce aut',
              'sales', 'prodej', 'channel development'],
    'HR': ['recruiter', 'personalist', 'náborář', 'recruitment', 'human resources', 
           'hr business partner', 'hr generalist', 'hr specialist', 'hr manager', 'talent acquisition'],
    'Marketing': ['marketing', 'seo', 'content', 'social media', 'brand', 'growth', 
                  'ppc', 'performance marketing', 'copywriter', 'redaktor', 'editor',
                  'hosteska', 'promotér'],
    'Support': ['support', 'customer', 'helpdesk', 'podpora', 'zákaznick', 'service desk'],
    'Operations': ['operations', 'admin', 'assistant', 'office manager', 'back office', 'koordinátor', 'referent',
                   'asistent', 'recepční'],
    'Finance': ['accountant', 'účetní', 'finance', 'controller', 'controlling', 'fakturant', 'auditor', 'ekonom', 'bankéř', 'banker'],
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
                  'řidič mhd', 'řidič autobusu', 'řidič kamionu', 'řidič vláček', 'řidička', 'řidiči',
                  'dispečer'],
    'Retail': ['prodavač', 'pokladní', 'prodejce', 'prodejn', 'obchod', 'prodejna', 'market', 'supermarket',
               'vedoucí prodejny', 'store manager', 'cashier', 'retail'],
    'Service': ['číšník', 'kuchař', 'recepční', 'barman', 'uklízeč', 'ostraha', 'security', 'hospodyně',
                'čerpací stanice', 'obsluha', 'údržba', 'technik údržby', 'servis', 'údržbář'],
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

# ============================================================================
# HYBRID CLASSIFIER: ML Embeddings with Keyword Fallback
# ============================================================================
# ARCHITECTURE:
#   1. Try ML embedding classification first (if available)
#   2. Fall back to keyword matching if:
#      - sentence-transformers not installed
#      - Model failed to load
#      - Embedding classification returned low confidence
#
# This gives us the best of both worlds:
#   - Better accuracy from semantic understanding
#   - Guaranteed functionality even without ML dependencies

# Try to import embedding classifier (may not be available)
try:
    from embedding_classifier import EmbeddingClassifier, EMBEDDINGS_AVAILABLE
    _USE_EMBEDDINGS = EMBEDDINGS_AVAILABLE
except ImportError:
    _USE_EMBEDDINGS = False
    EmbeddingClassifier = None


class JobClassifier:
    """
    Hybrid job classifier using ML embeddings with keyword fallback.

    DEBUGGING:
        from classifiers import JobClassifier
        JobClassifier.USE_EMBEDDINGS = False  # Force keyword mode

        # Or check which mode is active:
        print(JobClassifier.get_classification_mode())
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
        """Classify job into role category using hybrid approach.

        HYBRID STRATEGY (PRECISION-FIRST):
        1. Try keyword matching first (reliable explicit mapping)
        2. Fall back to ML embeddings for fuzzy/semantic matching
        """
        # 1. Keyword-based matching (Primary Source of Truth)
        keyword_result = JobClassifier._classify_role_keywords(title, description)
        if keyword_result != "Other":
            return keyword_result

        # 2. Try embedding classification as fallback
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
        """Keyword-based role classification (original implementation).

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
            if keyword in ['hr', 'it', 'pr', 'ui', 'ux', 'grafik', 'qa', 'sales']:
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
        
        # 3. "Architect" in Construction vs IT context
        if matched_role == 'Construction' and 'architekt' in title_lower:
             if any(kw in text for kw in ['software', 'solution', 'cloud', 'system', 'integration', 'data', 'it ', 'security']):
                 return 'Developer'

        # 4. "Developer" in Real Estate context
        if matched_role == 'Developer':
            if 'developersk' in text or ('developer' in title_lower and any(kw in text for kw in ['real estate', 'nemovitost', 'bytov', 'pozem'])):
                return 'Construction' # Or Management/Operations
            
            # 5. Hardware/Electrical Engineers are not Software Developers
            if any(kw in text for kw in ['analog', 'electrical', 'elektro', 'hardware', 'pcb', 'obvod']):
                # Unless it's "embedded software"
                if 'software' not in text and 'firmware' not in text:
                    return 'Electromechanics'

        # Downgrade low-level "Management" or Tech-focused leads to actual role category
        if matched_role == 'Management':
            # 1. Check for Tech Lead / Engineering Lead (should be Developer)
            tech_indicators = ['tech', 'software', 'engineer', 'development', 'it ', 'vývoj', 'programátor']
            if any(indicator in title_lower for indicator in tech_indicators):
                 # EXCEPTION: Channel/Business Development is NOT Tech
                 if 'business development' in title_lower or 'channel development' in title_lower or 'sales development' in title_lower:
                      return 'Sales'
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
        # "Sales Executive", "Account Executive" -> standard industry title inflation
        if 'executive' in title_lower and not any(x in title_lower for x in ['head', 'director', 'chief', 'c-level', 'vp', 'president', 'ředitel']):
             if 'sales' in title_lower or 'account' in title_lower:
                 return 'Sales'
             # For others, don't return 'Mid' as a role! Just let it fall through to other keywords
             # (e.g. 'Executive Assistant' will match 'assistant' -> Operations)

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

        # P2 FIX: Downgrade vedoucí/mistr from Executive to Lead (not C-level roles)
        non_executive_mgmt = ['vedoucí', 'mistr', 'směnový', 'store manager', 'vedoucí prodejny',
                              'vedoucí skladu', 'vedoucí směny', 'shift']
        is_non_exec_mgmt = any(term in title_lower for term in non_executive_mgmt)

        # First pass: Check title only (most reliable)
        for level in priority_order:
            patterns = SENIORITY_PATTERNS[level]
            if any(p in title_lower for p in patterns):
                # Downgrade Executive to Lead if it's a non-C-level management role
                if level == 'Executive' and is_non_exec_mgmt:
                    return 'Lead'
                return level

        # Second pass: Check description only if not found in title
        for level in priority_order:
            # SAFETY: Never match 'Executive' from description (too many false positives)
            if level == 'Executive':
                continue

            patterns = SENIORITY_PATTERNS[level]
            if any(p in desc_lower for p in patterns):
                return level

        return 'Mid'  # Default to Mid if unclear
