import pandas as pd
import analyzer

# Load Intelligence Core
intel = analyzer.MarketIntelligence()
df = intel.df

print(f"--- EXECUTIVE STRATEGY AUDIT (Data-Driven) ---")
print(f"Total Signals Analyzed: {len(df)}")

# 1. ANALYZE GHOST JOBS (Churn/Stability)
ghosts = intel.get_ghost_job_index()
avg_ghost_score = ghosts['Ghost Score'].mean() if not ghosts.empty else 0
print(f"\n[1] GHOST INDEX: Top 10 Serial Reposters identified. Avg Repost Rate: {avg_ghost_score:.1f}")
# If high churn -> Market is unstable, opportunity to offer STABILITY.

# 2. ANALYZE CONTRACT REALITY (HPP vs ICO)
contracts = intel.get_contract_split()
total_contracts = sum(contracts.values())
hpp_share = (contracts.get('HPP (Employment)', 0) / total_contracts) * 100
ico_share = (contracts.get('IČO (Contract)', 0) / total_contracts) * 100
print(f"\n[2] CONTRACT REALITY: HPP: {hpp_share:.1f}% | IČO: {ico_share:.1f}%")
# If IČO is high -> Market is fragile. HPP is a strong differentiator.

# 3. ANALYZE REMOTE TRUTH
remote = intel.get_remote_truth()
true_remote_share = (remote.get('True Remote', 0) / len(df)) * 100
fake_remote_share = (remote.get('Fake Remote (Bait)', 0) / len(df)) * 100
print(f"\n[3] REMOTE TRUTH: True Remote: {true_remote_share:.1f}% | Fake/Bait: {fake_remote_share:.1f}%")
# If True Remote is low -> It's the cheapest "Super Benefit" to offer.

# 4. ANALYZE TECH LAG
stack = intel.get_tech_stack_lag()
modern_vol = sum(stack['Modern'].values())
legacy_vol = sum(stack['Legacy'].values())
print(f"\n[4] TECH STACK: Modern Keywords: {modern_vol} | Legacy Keywords: {legacy_vol}")
# If Legacy is high -> Engineers are bored. Offer Modern stack to poach.

# 5. ANALYZE ENGLISH BARRIER
lang = intel.get_language_barrier()
en_only_share = (lang.get('English Only (Ocean)', 0) / len(df)) * 100
print(f"\n[5] ENGLISH BARRIER: English-Only Roles: {en_only_share:.1f}%")
# If this is low (<10%) -> The biggest arbitrage opportunity is hiring non-Czech speakers.

# --- SYNTHESIS ---
print("\n--- STRATEGIC KEYPOINT ---")
scores = {
    "OFFER STABILITY (HPP)": (100 - hpp_share) if hpp_share < 50 else 0,
    "OFFER TRUE REMOTE": (100 - true_remote_share) if true_remote_share < 10 else 0,
    "HIRE EXPATS (EN ONLY)": (100 - en_only_share) if en_only_share < 15 else 0,
    "MODERN STACK": (legacy_vol / max(modern_vol, 1)) * 50
}
winner = max(scores, key=scores.get)
print(f"RECOMMENDED FOCUS: {winner} (Score: {scores[winner]:.1f})")
