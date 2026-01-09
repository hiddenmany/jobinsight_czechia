"""
ML EMBEDDING CLASSIFIER FOR JOB ROLE CLASSIFICATION
====================================================

This module implements semantic embedding-based classification for job roles,
replacing keyword matching with vector similarity for better accuracy.

ARCHITECTURE OVERVIEW:
---------------------
1. We use a multilingual sentence transformer model that understands both
   Czech and English text (paraphrase-multilingual-MiniLM-L12-v2).
   
2. Each role category has "exemplar phrases" that define what that role means.
   These are converted to embeddings once at module load time.
   
3. When classifying a job, we:
   a) Combine title + description into a single text
   b) Convert to embedding vector (384 dimensions)
   c) Compare to each role's exemplar embedding using cosine similarity
   d) Return the role with highest similarity (if above threshold)

DEBUGGING STRATEGY:
------------------
- Set DEBUG_EMBEDDINGS=True to see similarity scores for every classification
- The get_debug_scores() method returns all scores for inspection
- If classification seems wrong, check:
  1. Is the similarity below SIMILARITY_THRESHOLD? (defaults to "Other")
  2. Are there competing high-scoring roles? (ambiguous job)
  3. Is the text mostly non-job content? (noise in description)

FALLBACK BEHAVIOR:
-----------------
If sentence-transformers is not installed or model fails to load:
- EMBEDDINGS_AVAILABLE will be False
- All calls gracefully fall back to keyword-based classification
- No exceptions or crashes - the app continues working

PERFORMANCE NOTES:
-----------------
- Model load: ~2-3 seconds, 420MB RAM
- Classification: ~50ms per job (GPU: ~5ms)
- Batch classification available for bulk processing
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger('HR-Intel-Embeddings')

# ============================================================================
# CONFIGURATION FLAGS
# ============================================================================

# Set to True to print similarity scores for every classification
DEBUG_EMBEDDINGS = False

# Minimum similarity score to assign a role (below this → "Other")
# TUNING GUIDE:
#   - Too low (0.2): Everything gets classified, many false positives
#   - Too high (0.6): Many jobs fall to "Other", false negatives
#   - CALIBRATION (2026-01-07): Raised to 0.40 to prioritize precision over recall.
SIMILARITY_THRESHOLD = 0.40

# ============================================================================
# MODEL INITIALIZATION
# ============================================================================

# Attempt to load the embedding model
# This is wrapped in try/except for graceful degradation
EMBEDDINGS_AVAILABLE = False
_model = None
_role_embeddings = None
_seniority_embeddings = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    
    # Model selection rationale:
    # - paraphrase-multilingual-MiniLM-L12-v2: Best balance of size/quality for multilingual
    # - Supports 50+ languages including Czech
    # - 384 dimensions (smaller than alternatives)
    # - ~420MB download, ~120MB RAM after loading
    MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    
    logger.info(f"Loading embedding model: {MODEL_NAME}")
    _model = SentenceTransformer(MODEL_NAME)
    logger.info("Embedding model loaded successfully")
    
    EMBEDDINGS_AVAILABLE = True
    
except ImportError:
    logger.warning(
        "sentence-transformers not installed. "
        "Role classification will use keyword fallback. "
        "Install with: pip install sentence-transformers"
    )
except Exception as e:
    logger.warning(f"Failed to load embedding model: {e}. Using keyword fallback.")


# ============================================================================
# ROLE EXEMPLARS
# ============================================================================
# These phrases define what each role "means" semantically.
# The model understands these are related concepts, not just keywords.
#
# DESIGN DECISIONS:
# - Mix Czech + English phrases for cross-lingual matching
# - Include common variations and synonyms
# - Include typical tasks/responsibilities, not just titles
# - Avoid overlapping phrases between categories

ROLE_EXEMPLARS = {
    'Developer': """
        software developer programmer software engineer vývojář programátor
        frontend backend fullstack web developer mobile developer
        devops platform engineer SRE site reliability
        coding programming building software applications
        Python Java JavaScript React Angular Vue Node.js
        architect solution architect software architect
    """,
    
    'Analyst': """
        data analyst business analyst analytik datový analytik
        data scientist machine learning AI engineer
        BI analyst reporting analytics visualization
        SQL database queries data modeling statistics
        market research competitive analysis insights
    """,
    
    'Designer': """
        UX designer UI designer product designer grafik
        visual designer creative director art director
        user experience user interface wireframes prototypes
        Figma Sketch Adobe XD design systems
        graphic design brand identity visual communication
    """,
    
    'QA': """
        QA engineer tester test engineer quality assurance
        automation testing selenium cypress playwright
        SDET software development engineer in test
        test cases bug reports quality control
        manual testing regression testing performance testing
    """,
    
    'PM': """
        project manager product manager projektový manažer
        scrum master agile coach product owner
        delivery manager program manager
        roadmap sprint planning backlog grooming
        stakeholder management cross-functional coordination
    """,
    
    'Sales': """
        sales representative obchodní zástupce account manager
        business development key account manager sales manager
        prodejce obchodník account executive
        customer acquisition pipeline CRM negotiations deals
        B2B B2C enterprise sales inside sales field sales
    """,
    
    'HR': """
        HR recruiter personalist náborář human resources
        talent acquisition recruitment headhunter
        HR business partner HR generalist HR specialist
        employee relations onboarding performance management
        compensation benefits payroll HRIS
    """,
    
    'Marketing': """
        marketing specialist marketing manager marketér
        digital marketing SEO SEM content marketing
        social media brand manager growth hacker
        PPC performance marketing copywriter editor
        campaigns email marketing marketing automation
    """,
    
    'Support': """
        customer support helpdesk zákaznická podpora
        technical support service desk customer service
        troubleshooting ticketing user assistance
        call center contact center customer care
    """,
    
    'Operations': """
        operations manager administrator asistent office manager
        back office coordinator administrative assistant
        executive assistant operations coordinator
        scheduling logistics office administration
    """,
    
    'Finance': """
        accountant účetní financial controller auditor
        finance manager CFO ekonom fakturant
        budgeting forecasting financial analysis
        AP AR general ledger tax compliance
        banker bankéř financial advisor investment
    """,
    
    'Management': """
        CEO CTO CFO COO director ředitel
        VP vice president head of department
        general manager managing director C-level executive
        strategic leadership executive management
        board member chief officer senior leadership
    """,
    
    'Healthcare': """
        doctor nurse lékař sestra zdravotní
        pharmacist psychologist physiotherapist
        medical healthcare clinical patient care
        hospital clinic medical practice
    """,
    
    'Manufacturing': """
        operator výroby dělník montážník svářeč
        CNC machine operator production worker
        manufacturing assembly line factory floor
        quality control production line technician
        zámečník elektrikář seřizovač
    """,
    
    'Logistics': """
        warehouse skladník řidič driver logistics
        dispatcher kurýr disponent spediter
        supply chain shipping receiving forklift
        inventory management distribution transportation
    """,
    
    'Retail': """
        store manager prodavač cashier pokladní
        retail sales associate shop assistant
        customer service retail merchandising
        prodejna obchod supermarket
    """,
    
    'Service': """
        waiter číšník cook kuchař bartender
        hotel hospitality restaurant food service
        cleaning maintenance housekeeping security
        receptionist front desk concierge
    """,
    
    'Legal': """
        lawyer právník paralegal attorney advokát
        legal counsel compliance officer notary
        contracts litigation regulatory affairs
        legal assistant law firm
    """,
    
    'Construction': """
        construction stavbyvedoucí site manager
        architect projektant civil engineer
        electrician plumber installer
        building renovation infrastructure
    """,
    
    'Education': """
        teacher učitel professor lecturer
        trainer educator instructor coach
        curriculum development teaching tutoring
        school university training
    """,
}

# ============================================================================
# SENIORITY EXEMPLARS
# ============================================================================
# Similar approach for seniority detection

SENIORITY_EXEMPLARS = {
    'Junior': """
        junior entry level trainee intern graduate
        absolvent začátečník 0-2 years experience
        fresh graduate recent graduate first job
        learning developing skills mentorship
    """,
    
    'Mid': """
        mid level regular medior 2-5 years experience
        independent contributor professional
        autonomous work moderate experience
    """,
    
    'Senior': """
        senior experienced sr specialist expert
        5+ years 5-10 years zkušený pokročilý
        deep expertise technical authority
        mentoring others decision making
    """,
    
    'Lead': """
        lead principal staff architect team lead
        tech lead engineering lead chapter lead
        leading a team managing engineers
        technical leadership people management
    """,
    
    'Executive': """
        CEO CTO CFO COO VP vice president
        chief executive director ředitel C-level
        head of department executive leadership
        board strategic vision company-wide
    """,
}


# ============================================================================
# PRE-COMPUTE EMBEDDINGS AT MODULE LOAD
# ============================================================================

def _compute_role_embeddings() -> Optional[Dict[str, np.ndarray]]:
    """
    Convert all role exemplar texts to embedding vectors.
    
    Called once at module load. If this fails, we fall back to keywords.
    
    Returns:
        Dict mapping role name -> embedding vector (384 dims)
    """
    if not EMBEDDINGS_AVAILABLE:
        return None
    
    try:
        embeddings = {}
        for role, exemplar_text in ROLE_EXEMPLARS.items():
            # Clean up the text (remove extra whitespace)
            clean_text = ' '.join(exemplar_text.split())
            # Encode to vector
            embeddings[role] = _model.encode(clean_text, convert_to_numpy=True)
        
        logger.info(f"Pre-computed embeddings for {len(embeddings)} roles")
        return embeddings
    
    except Exception as e:
        logger.error(f"Failed to compute role embeddings: {e}")
        return None


def _compute_seniority_embeddings() -> Optional[Dict[str, np.ndarray]]:
    """
    Convert all seniority exemplar texts to embedding vectors.
    """
    if not EMBEDDINGS_AVAILABLE:
        return None
    
    try:
        embeddings = {}
        for level, exemplar_text in SENIORITY_EXEMPLARS.items():
            clean_text = ' '.join(exemplar_text.split())
            embeddings[level] = _model.encode(clean_text, convert_to_numpy=True)
        
        logger.info(f"Pre-computed embeddings for {len(embeddings)} seniority levels")
        return embeddings
    
    except Exception as e:
        logger.error(f"Failed to compute seniority embeddings: {e}")
        return None


# Initialize embeddings at module load
if EMBEDDINGS_AVAILABLE:
    _role_embeddings = _compute_role_embeddings()
    _seniority_embeddings = _compute_seniority_embeddings()
    
    # If embedding computation failed, disable embeddings
    if _role_embeddings is None:
        EMBEDDINGS_AVAILABLE = False
        logger.warning("Embedding computation failed, falling back to keywords")


# ============================================================================
# SIMILARITY FUNCTIONS
# ============================================================================

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Cosine similarity measures the angle between vectors, not magnitude.
    Range: -1 (opposite) to 1 (identical)
    
    For normalized vectors (which sentence-transformers produces),
    this is equivalent to dot product.
    
    Args:
        vec1: First embedding vector
        vec2: Second embedding vector
        
    Returns:
        Similarity score between -1 and 1
    """
    # Normalize vectors
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def get_all_similarities(
    text: str,
    embeddings_dict: Dict[str, np.ndarray]
) -> Dict[str, float]:
    """
    Compute similarity between input text and all categories.
    
    This is the core function for debugging - it shows how the model
    "sees" the input text across all possible categories.
    
    Args:
        text: Input text (title + description)
        embeddings_dict: Pre-computed category embeddings
        
    Returns:
        Dict mapping category name -> similarity score
    """
    if not EMBEDDINGS_AVAILABLE or _model is None:
        return {}
    
    try:
        # Encode the input text
        text_embedding = _model.encode(text, convert_to_numpy=True)
        
        # Compute similarity to each category
        similarities = {}
        for category, category_embedding in embeddings_dict.items():
            similarities[category] = cosine_similarity(text_embedding, category_embedding)
        
        return similarities
    
    except Exception as e:
        logger.error(f"Error computing similarities: {e}")
        return {}


# ============================================================================
# MAIN CLASSIFIER CLASS
# ============================================================================

class EmbeddingClassifier:
    """
    ML-based job classifier using semantic embeddings.
    
    USAGE:
        role = EmbeddingClassifier.classify_role("Python Developer", "We need Django...")
        seniority = EmbeddingClassifier.classify_seniority("Senior Engineer", "5+ years...")
    
    DEBUGGING:
        # See all similarity scores
        scores = EmbeddingClassifier.get_role_debug_scores("Python Developer", "Django...")
        print(scores)  # {'Developer': 0.72, 'Analyst': 0.31, ...}
    
    FALLBACK:
        If embeddings not available, returns None (caller should use keyword fallback)
    """
    
    @staticmethod
    def classify_role(title: str, description: str = "") -> Optional[str]:
        """
        Classify job into a role category using semantic similarity.
        
        Algorithm:
        1. Combine title + description (title weighted more by being first)
        2. Convert to embedding vector
        3. Compare to each role's exemplar embedding
        4. Return role with highest similarity above threshold
        
        Args:
            title: Job title (e.g., "Senior Python Developer")
            description: Job description text
            
        Returns:
            Role category (e.g., "Developer") or None if embeddings unavailable
        """
        if not EMBEDDINGS_AVAILABLE or _role_embeddings is None:
            return None  # Caller should fall back to keyword matching
        
        # Combine text with title emphasis
        # Title appears twice to give it more weight in the embedding
        combined_text = f"{title} {title} {description[:500]}"
        
        similarities = get_all_similarities(combined_text, _role_embeddings)
        
        if not similarities:
            return None
        
        # Debug output if enabled
        if DEBUG_EMBEDDINGS:
            sorted_scores = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            logger.debug(f"Role scores for '{title[:50]}...':")
            for role, score in sorted_scores[:5]:
                logger.debug(f"  {role}: {score:.3f}")
        
        # Find best match
        best_role = max(similarities, key=similarities.get)
        best_score = similarities[best_role]
        
        # Apply threshold
        if best_score < SIMILARITY_THRESHOLD:
            if DEBUG_EMBEDDINGS:
                logger.debug(f"  -> 'Other' (best score {best_score:.3f} < threshold {SIMILARITY_THRESHOLD})")
            return "Other"
        
        return best_role
    
    @staticmethod
    def classify_seniority(title: str, description: str = "") -> Optional[str]:
        """
        Classify job seniority level using semantic similarity.
        
        Note: Seniority is often less reliable via embeddings because:
        - Many job postings don't mention seniority
        - Seniority keywords are more reliable (Senior/Junior are explicit)
        
        Consider using keyword matching for seniority as primary,
        with embeddings as tie-breaker.
        
        Returns:
            Seniority level (e.g., "Senior") or None if unavailable
        """
        if not EMBEDDINGS_AVAILABLE or _seniority_embeddings is None:
            return None
        
        combined_text = f"{title} {description[:300]}"
        similarities = get_all_similarities(combined_text, _seniority_embeddings)
        
        if not similarities:
            return None
        
        # Debug output
        if DEBUG_EMBEDDINGS:
            sorted_scores = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
            logger.debug(f"Seniority scores for '{title[:50]}...':")
            for level, score in sorted_scores:
                logger.debug(f"  {level}: {score:.3f}")
        
        # For seniority, use a higher threshold since keywords are more reliable
        best_level = max(similarities, key=similarities.get)
        best_score = similarities[best_level]
        
        # Higher threshold for seniority (0.45) since it's less reliable
        if best_score < 0.45:
            return None  # Let keyword matching decide
        
        return best_level
    
    @staticmethod
    def get_role_debug_scores(title: str, description: str = "") -> Dict[str, float]:
        """
        Get all role similarity scores for debugging.
        
        Use this to understand why a job was classified a certain way.
        
        Example:
            scores = EmbeddingClassifier.get_role_debug_scores("Python Developer", "Django backend")
            # Returns: {'Developer': 0.72, 'Analyst': 0.31, 'Management': 0.15, ...}
        """
        if not EMBEDDINGS_AVAILABLE or _role_embeddings is None:
            return {}
        
        combined_text = f"{title} {title} {description[:500]}"
        return get_all_similarities(combined_text, _role_embeddings)
    
    @staticmethod
    def get_seniority_debug_scores(title: str, description: str = "") -> Dict[str, float]:
        """Get all seniority similarity scores for debugging."""
        if not EMBEDDINGS_AVAILABLE or _seniority_embeddings is None:
            return {}
        
        combined_text = f"{title} {description[:300]}"
        return get_all_similarities(combined_text, _seniority_embeddings)
    
    @staticmethod
    def is_available() -> bool:
        """Check if embedding classification is available."""
        return EMBEDDINGS_AVAILABLE and _role_embeddings is not None


# ============================================================================
# BATCH PROCESSING (for re-analyzing existing data)
# ============================================================================

def classify_roles_batch(
    jobs: List[Tuple[str, str]]
) -> List[str]:
    """
    Classify multiple jobs efficiently using batch encoding.
    
    This is ~3x faster than individual calls for large datasets
    because the model can parallelize the encoding.
    
    Args:
        jobs: List of (title, description) tuples
        
    Returns:
        List of role classifications
    """
    if not EMBEDDINGS_AVAILABLE or _role_embeddings is None:
        return [None] * len(jobs)
    
    try:
        # Prepare texts
        texts = [f"{title} {title} {desc[:500]}" for title, desc in jobs]
        
        # Batch encode
        embeddings = _model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        
        # Classify each
        results = []
        for text_embedding in embeddings:
            similarities = {
                role: cosine_similarity(text_embedding, role_emb)
                for role, role_emb in _role_embeddings.items()
            }
            
            best_role = max(similarities, key=similarities.get)
            best_score = similarities[best_role]
            
            if best_score < SIMILARITY_THRESHOLD:
                results.append("Other")
            else:
                results.append(best_role)
        
        return results
    
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        return [None] * len(jobs)


# ============================================================================
# QUICK TEST (run this file directly to test)
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("EMBEDDING CLASSIFIER TEST")
    print("=" * 60)
    
    if not EMBEDDINGS_AVAILABLE:
        print("❌ Embeddings not available. Install with:")
        print("   pip install sentence-transformers")
        exit(1)
    
    print(f"✓ Model loaded: {MODEL_NAME}")
    print(f"✓ Roles: {len(_role_embeddings)}")
    print(f"✓ Seniority levels: {len(_seniority_embeddings)}")
    print()
    
    # Test cases
    test_jobs = [
        ("Python Developer", "We need someone with Django and FastAPI experience"),
        ("Pythonista", "Hledáme zkušeného programátora"),
        ("Osobní bankéř/ka", "Práce v bance, poradenství klientům"),
        ("Vedoucí prodejny", "Řízení týmu v supermarketu"),
        ("CTO", "Chief Technology Officer for our startup"),
        ("Číšník", "Obsluha hostů v restauraci"),
        ("PRODUKTOVÝ INŽENÝR", "Vývoj nových produktů"),
    ]
    
    print("Role Classification Results:")
    print("-" * 60)
    for title, desc in test_jobs:
        role = EmbeddingClassifier.classify_role(title, desc)
        scores = EmbeddingClassifier.get_role_debug_scores(title, desc)
        top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        print(f"\n'{title}'")
        print(f"  → {role}")
        print(f"  Top 3: {', '.join(f'{r}:{s:.2f}' for r, s in top_3)}")
