import sys
import os

# Add project path to sys.path
sys.path.append(r'C:\Users\phone\Desktop\JobsCzInsight')

from classifiers import JobClassifier

titles = [
    "Channel Development Manager - HoReCa segment",
    "COST MANAŽER/KA v DEVELOPERSKÉ SPOLEČNOSTI",
    "Sales Specialist",
    "ASISTENTKA architektonického ateliéru",
    "DISPEČER SENIOR",
    "Biomedicínský inženýr",
    "Eletrikář",
    "Salesforce Konzultant"
]

print(f"{'TITLE':<50} | {'KEYWORD':<15} | {'MODE'}")
print("-" * 80)

for title in titles:
    # Force keyword mode to see if it's the keywords or ML
    JobClassifier.USE_EMBEDDINGS = False
    kw_result = JobClassifier.classify_role(title)
    
    print(f"{title[:50]:<50} | {kw_result:<15} | KEYWORD_ONLY")