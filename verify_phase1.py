from tools.whitelist_discovery import extract_candidates_from_text, calculate_proximity_score

# Verify extraction
text = "Experience with Java and Kubernetes is required."
candidates = extract_candidates_from_text([text])
print(f"Candidates extracted: {list(candidates.keys())}")

# Verify proximity
score = calculate_proximity_score(text, "kubernetes", ["java"])
print(f"Proximity Score: {score}")

assert "kubernetes" in candidates
assert score == 1.0
print("Verification SUCCESS")
