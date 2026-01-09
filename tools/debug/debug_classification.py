from classifiers import JobClassifier
from embedding_classifier import EmbeddingClassifier

def test_job(title, desc=""):
    print(f"\nTESTING: '{title}'")
    
    # 1. Role Classification
    role = JobClassifier.classify_role(title, desc)
    print(f"  Result Role: {role}")
    
    if EmbeddingClassifier.is_available():
        scores = EmbeddingClassifier.get_role_debug_scores(title, desc)
        top_3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"  Top 3 Role Scores: {', '.join(f'{r}:{s:.3f}' for r, s in top_3)}")
    
    # 2. Seniority Classification
    seniority = JobClassifier.detect_seniority(title, desc)
    print(f"  Result Seniority: {seniority}")

print("--- DEBUGGING MISCLASSIFICATIONS ---")
test_job("Svářeč", "Hledáme svářeče pro naši výrobu.")
test_job("SEŘIZOVAČ CNC STROJŮ - frézka")
test_job("SKLADNÍK NA LETIŠTI", "Budete pracovat pod vedením Ředitele logistiky.")
test_job("Svářeč", "Společnost Sécheron Hasler CZ, spol. s r.o. hledá svářeče.")
