import re
import duckdb
import os
import datetime
from collections import Counter
from typing import List, Dict
from settings import settings

# Try import google-genai, handle failure gracefully
try:
    from google import genai
except ImportError:
    genai = None

# Basic stopword list (expand as needed)
STOPWORDS = set([
    'a', 'an', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'and', 'or', 'is', 'are', 'was', 'were',
    'a', 'v', 'na', 'k', 'pro', 'z', 's', 'o', 'do', 've', 'se', 'že', 'je', 'jsou', 'byl', 'byla', 'to', 'co',
    'i', 'ale', 'jako', 'nebo', 'když', 'aby', 'kde', 'kdo', 'kam', 'jak', 'tak', 'už', 'jen', 'tam',
    'we', 'you', 'our', 'your',
    'my', 'vy', 'náš', 'váš',
    'dobrá', 'výhodou', 'nabízíme', 'požadujeme', 'hledáme'
])

def clean_text(text: str) -> List[str]:
    """Tokenize and clean text."""
    # Lowercase
    text = text.lower()
    # Remove special chars (keep alphanumeric and basic punctuation for splitting)
    # We keep alphanumeric and Czech chars.
    text = re.sub(r'[^a-z0-9áčďéěíňóřšťúůýž]', ' ', text)
    # Split by whitespace
    tokens = text.split()
    # Remove stopwords and short words
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens

def generate_ngrams(tokens: List[str], n: int) -> List[str]:
    """Generate n-grams from tokens."""
    if len(tokens) < n:
        return []
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def extract_candidates_from_text(texts: List[str]) -> Dict[str, int]:
    """
    Extract 1-3 grams from a list of texts and return frequency counts.
    """
    counter = Counter()
    
    for text in texts:
        tokens = clean_text(text)
        
        # 1-grams
        counter.update(tokens)
        
        # 2-grams
        counter.update(generate_ngrams(tokens, 2))
        
        # 3-grams
        counter.update(generate_ngrams(tokens, 3))
        
    return dict(counter)

def calculate_significance(freq: int, total_docs: int) -> float:
    """
    Calculate simple significance score (frequency / total_docs).
    """
    if total_docs == 0:
        return 0.0
    return freq / total_docs

def extract_candidates_from_db(min_count: int = 5) -> Dict[str, int]:
    """
    Extract frequent terms from 'Other' jobs in the database.
    """
    db_path = str(settings.get_db_path())
    con = duckdb.connect(db_path, read_only=True)
    
    # Select titles and descriptions for 'Other' roles
    # We assume the table is 'signals' and it has 'role_category'
    try:
        query = """
        SELECT title, description 
        FROM signals 
        WHERE role_type = 'Other' 
        AND description IS NOT NULL
        """
        
        df = con.execute(query).df()
    except duckdb.CatalogException:
        # Fallback if table doesn't exist (e.g. testing)
        con.close()
        return {}
        
    con.close()
    
    if df.empty:
        return {}

    # Combine title and description
    texts = (df['title'] + " " + df['description']).tolist()
    
    candidates = extract_candidates_from_text(texts)
    
    # Filter by min_count
    return {k: v for k, v in candidates.items() if v >= min_count}

def calculate_proximity_score(text: str, term: str, context_keywords: List[str], window: int = 5) -> float:
    """
    Check if a term appears within `window` words of any context keyword.
    Returns 1.0 if match, 0.0 otherwise.
    """
    tokens = clean_text(text)
    term_tokens = clean_text(term)
    
    if not term_tokens:
        return 0.0
        
    term_len = len(term_tokens)
    first_term_token = term_tokens[0]
    
    term_indices = [i for i, t in enumerate(tokens) if t == first_term_token]
    
    # Verify full n-gram match at these indices
    valid_term_indices = []
    for idx in term_indices:
        # Slice safely
        if tokens[idx:idx+term_len] == term_tokens:
            valid_term_indices.append(idx)
            
    if not valid_term_indices:
        return 0.0
        
    # Find context indices
    context_indices = []
    for keyword in context_keywords:
        kw_tokens = clean_text(keyword)
        if not kw_tokens: continue
        kw_len = len(kw_tokens)
        first_kw = kw_tokens[0]
        
        kw_starts = [i for i, t in enumerate(tokens) if t == first_kw]
        for idx in kw_starts:
            if tokens[idx:idx+kw_len] == kw_tokens:
                context_indices.append(idx)
                
    if not context_indices:
        return 0.0
        
    # Check minimum distance
    for t_idx in valid_term_indices:
        for c_idx in context_indices:
            # If term overlaps with context keyword (e.g. "java" vs "java developer"), 
            # treat as proximity 0 which is <= window.
            # We treat the start index distance.
            dist = abs(t_idx - c_idx)
            if dist <= window:
                return 1.0
                
    return 0.0

def validate_candidates_with_llm(candidates: List[str]) -> Dict[str, str]:
    """
    Validate a list of candidate terms using Gemini.
    Returns a dictionary {term: classification}.
    Classification can be 'Tech', 'Non-Tech', 'Unrelated'.
    """
    if not candidates:
        return {}
        
    # Check if genai is available
    if not genai:
        print("google-genai not installed. Skipping LLM validation.")
        return {c: 'Unrelated' for c in candidates}
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set. Skipping LLM validation.")
        return {c: 'Unrelated' for c in candidates}
        
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Classify the following terms into one of these categories:
    - Tech: A specific technical skill, programming language, tool, framework, or IT job role (e.g., Python, AWS, Scrum Master, React).
    - Non-Tech: A professional skill or role but NOT specific to IT/Engineering (e.g., Driver, Accountant, Sales).
    - Unrelated: Garbage text, stopwords, or irrelevant words.
    
    Output the result as a list in the format: "Term: Category"
    
    Terms to classify:
    """ + "\n".join(candidates)
    
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
    except Exception as e:
        print(f"LLM Error: {e}")
        return {c: 'Error' for c in candidates}
    
    results = {}
    if response.text:
        for line in response.text.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                term = parts[0].strip()
                category = parts[1].strip()
                # Simple normalization
                if 'Tech' in category and 'Non-Tech' not in category:
                    results[term] = 'Tech'
                elif 'Non-Tech' in category:
                    results[term] = 'Non-Tech'
                else:
                    results[term] = 'Unrelated'
                    
    # Fill in missing as Unrelated or handle error
    for c in candidates:
        if c not in results:
            results[c] = 'Unrelated' # Default fallback
            
    return results

def update_classifiers_file(new_terms: List[str], file_path: str = None) -> bool:
    """
    Update the tech_protection list in classifiers.py with new terms.
    """
    if not file_path:
        # Default path
        file_path = os.path.join(settings.BASE_DIR, 'classifiers.py')
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex to find tech_protection list assignment
        # Look for: tech_protection = ['software', ...]
        pattern = r"(tech_protection\s*=\s*\[)(.*?)(\])"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            print(f"Could not find tech_protection list in {file_path}")
            return False
            
        current_list_str = match.group(2)
        # Parse current items
        # Simple split by comma and strip quotes
        current_items = [
            item.strip().strip("'").strip('"') 
            for item in current_list_str.split(',') 
            if item.strip()
        ]
        
        # Add new terms if not present
        updated = False
        for term in new_terms:
            if term not in current_items:
                current_items.append(term)
                updated = True
                
        if not updated:
            return True # Nothing to do, but success
            
        # Reconstruct list string
        # Maintain single quotes for consistency
        new_list_str = ", ".join([f"'{item}'" for item in current_items])
        
        # Replace in content
        new_content = content[:match.start(2)] + new_list_str + content[match.end(2):]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True
        
    except Exception as e:
        print(f"Failed to update classifiers file: {e}")
        return False

def format_report(results: Dict[str, str], added_terms: List[str]) -> str:
    """Format the whitelist analysis results as Markdown."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = [f"# Whitelist Auto-update Report ({timestamp})\n"]
    
    report.append("## Automatically Added Terms")
    if added_terms:
        for term in sorted(added_terms):
            report.append(f"- {term}")
    else:
        report.append("_No terms added automatically._")
        
    report.append("\n## Review Candidates")
    
    # Sort results
    # Group by classification
    grouped = {}
    for term, classification in results.items():
        if term in added_terms: continue # Skip added
        if classification not in grouped:
            grouped[classification] = []
        grouped[classification].append(term)
        
    if grouped:
        for classification, terms in grouped.items():
            report.append(f"\n### {classification}")
            for term in sorted(terms):
                report.append(f"- {term}")
    else:
        report.append("_No other candidates found._")
        
    return "\n".join(report)

def generate_report(results: Dict[str, str], added_terms: List[str]) -> None:
    """Generate and save the report."""
    content = format_report(results, added_terms)
    
    report_dir = os.path.join(settings.BASE_DIR, 'report')
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, 'whitelist_candidates.md')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Report saved to {report_path}")

def run_discovery(min_count: int = 5, dry_run: bool = True) -> Dict[str, int]:
    """
    Main orchestration function.
    """
    print(f"Starting whitelist discovery (min_count={min_count}, dry_run={dry_run})...")
    
    # 1. Extract
    print("Extracting candidates from DB...")
    candidates_count = extract_candidates_from_db(min_count=min_count)
    if not candidates_count:
        print("No candidates found matching criteria.")
        return {'processed': 0, 'added': 0}
        
    candidates = list(candidates_count.keys())
    print(f"Found {len(candidates)} candidates.")
    
    # 2. Validate
    print("Validating with LLM...")
    validation_results = validate_candidates_with_llm(candidates)
    
    # 3. Filter for High Confidence (Tech)
    tech_candidates = [term for term, cat in validation_results.items() if cat == 'Tech']
    print(f"Identified {len(tech_candidates)} Tech candidates.")
    
    # 4. Update (if not dry run)
    added_count = 0
    if not dry_run and tech_candidates:
        print("Updating classifiers.py...")
        if update_classifiers_file(tech_candidates):
            added_count = len(tech_candidates)
            print("Update successful.")
        else:
            print("Update failed.")
    elif dry_run and tech_candidates:
        print("Dry run: Skipping file update.")
        
    # 5. Report
    print("Generating report...")
    generate_report(validation_results, tech_candidates if not dry_run else [])
    
    return {
        'processed': len(candidates),
        'added': added_count
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Discover and auto-update tech whitelist.")
    parser.add_argument("--min-count", type=int, default=5, help="Minimum frequency count")
    parser.add_argument("--live", action="store_true", help="Execute actual update (disable dry-run)")
    
    args = parser.parse_args()
    
    run_discovery(min_count=args.min_count, dry_run=not args.live)