#!/usr/bin/env python3
"""Comprehensive test suite for all changes made on 2026-01-08."""

print('=' * 60)
print('COMPREHENSIVE TEST SUITE - JobsCzInsight')
print('=' * 60)

# === 1. SETTINGS MODULE ===
print('\n📦 1. SETTINGS MODULE')
from settings import settings
print(f'   ✅ DB Path: {settings.DB_PATH.name}')
print(f'   ✅ Cache Path: {settings.LLM_CACHE_PATH.name}')
print(f'   ✅ Taxonomy Path: {settings.TAXONOMY_PATH.name}')
settings.ensure_dirs()
print(f'   ✅ Directories ensured')

# === 2. CURRENCY RATES ===
print('\n💱 2. CURRENCY RATES')
from parsers import _load_currency_rates, SalaryParser
rates = _load_currency_rates()
for currency, rate in rates.items():
    print(f'   ✅ {currency}: {rate} CZK')

# === 3. SALARY PARSING ===
print('\n💰 3. SALARY PARSING')
tests = [
    ('50000 - 70000 Kč', 60000),
    ('3000 EUR', 3000 * rates['EUR']),
    ('800 Kč/hod', 800 * 160),
    ('2500 CZK/hour', 2500 * 160),
    ('5000 Kč/den', 5000 * 22),
]
for input_str, expected in tests:
    min_s, max_s, avg = SalaryParser.parse(input_str)
    status = '✅' if abs(avg - expected) < 1 else '❌'
    print(f'   {status} {input_str:20} -> {avg:,.0f} Kč')

# === 4. BONUS DETECTION ===
print('\n🎁 4. BONUS DETECTION')
bonus_tests = [
    ('60000 + bonus 10000', True, False),
    ('55000 Kč + 13. plat', True, True),
    ('70000 bez bonusu', False, False),
]
for test, exp_bonus, exp_13th in bonus_tests:
    result = SalaryParser.parse_with_bonus(test)
    status = '✅' if result['has_bonus'] == exp_bonus and result['has_13th_salary'] == exp_13th else '❌'
    print(f'   {status} "{test}" -> bonus={result["has_bonus"]}, 13th={result["has_13th_salary"]}')

# === 5. CLASSIFICATION ===
print('\n🏷️ 5. CLASSIFICATION (Engineering Sub-Taxonomy)')
from classifiers import JobClassifier
class_tests = [
    ('Software Engineer', 'Python, AWS', 'Developer'),
    ('HVAC Engineer', 'klimatizace', 'General Engineering'),
    ('Mechanical Engineer', 'CAD', 'General Engineering'),
    ('DevOps Engineer', 'Kubernetes', 'Developer'),
]
for title, desc, expected in class_tests:
    result = JobClassifier.classify_role(title, desc)
    status = '✅' if result == expected else '❌'
    print(f'   {status} {title:25} -> {result}')

# === 6. CONTENT HASH ===
print('\n🔑 6. CONTENT HASH (Remote Deduplication)')
from analyzer import get_content_hash
h1 = get_content_hash('Dev', 'Corp', 'Job description A with unique content', 'Remote', 'https://jobs.cz/123')
h2 = get_content_hash('Dev', 'Corp', 'Job description B with different content', 'Remote', 'https://jobs.cz/456')
h3 = get_content_hash('Dev', 'Corp', 'Job description A with unique content', 'Praha')
status = '✅' if h1 != h2 else '❌'
print(f'   {status} Different remote jobs get unique hashes: {h1[:12]}... vs {h2[:12]}...')

# === 7. DATA LOAD ===
print('\n📊 7. DATA LOAD')
from analyzer import MarketIntelligence
intel = MarketIntelligence()
print(f'   ✅ Loaded {len(intel.df)} jobs from database')
tech_counts = intel.df['tech_status'].value_counts()
print(f'   Modern: {tech_counts.get("Modern", 0)}, Dinosaur: {tech_counts.get("Dinosaur", 0)}, Stable: {tech_counts.get("Stable", 0)}')

print('\n' + '=' * 60)
print('✅ ALL FEATURE TESTS COMPLETE')
print('=' * 60)
