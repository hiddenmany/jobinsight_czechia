#!/usr/bin/env python3
"""
Data Quality Validation Script
Runs sanity checks on the JobsCzInsight database to detect corruption
"""
import duckdb
from settings import settings

DB_PATH = str(settings.get_db_path())

print("=" * 70)
print("DATA QUALITY VALIDATION REPORT")
print(f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

try:
    conn = duckdb.connect(DB_PATH, read_only=True)

    # Basic Stats
    total_jobs = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    print(f"\n[STATS] Total Jobs: {total_jobs:,}")

    # Test 1: Salary Sanity Checks
    print("\n" + "─" * 70)
    print("🔍 TEST 1: SALARY SANITY CHECKS")
    print("─" * 70)

    # Count jobs with salary data
    with_salary = conn.execute("SELECT COUNT(*) FROM signals WHERE avg_salary IS NOT NULL AND avg_salary > 0").fetchone()[0]
    salary_coverage = (with_salary / total_jobs) * 100
    print(f"Jobs with salary: {with_salary:,} ({salary_coverage:.1f}%)")

    # Suspiciously low salaries (< 15k CZK/month)
    too_low = conn.execute("SELECT COUNT(*) FROM signals WHERE avg_salary > 0 AND avg_salary < 15000").fetchone()[0]
    too_low_pct = (too_low / with_salary) * 100 if with_salary > 0 else 0
    status_low = "✅ PASS" if too_low_pct < 5 else "❌ FAIL"
    print(f"{status_low} Suspiciously low (<15k): {too_low} ({too_low_pct:.2f}%)")
    if too_low > 0:
        print("     ⚠️  These might be hourly rates that weren't converted!")
        samples = conn.execute("""
            SELECT title, company, avg_salary, salary_raw
            FROM signals
            WHERE avg_salary > 0 AND avg_salary < 15000
            LIMIT 3
        """).fetchall()
        for title, company, sal, raw in samples:
            print(f"        - {title} @ {company}: {sal:.0f} CZK (raw: {raw})")

    # Suspiciously high salaries (> 300k CZK/month)
    too_high = conn.execute("SELECT COUNT(*) FROM signals WHERE avg_salary > 300000").fetchone()[0]
    too_high_pct = (too_high / with_salary) * 100 if with_salary > 0 else 0
    status_high = "✅ PASS" if too_high_pct < 1 else "⚠️  WARN"
    print(f"{status_high} Suspiciously high (>300k): {too_high} ({too_high_pct:.2f}%)")
    if too_high > 0:
        print("     ℹ️  These might be executive roles or parsing errors (10x inflation)")
        samples = conn.execute("""
            SELECT title, company, avg_salary, salary_raw
            FROM signals
            WHERE avg_salary > 300000
            LIMIT 3
        """).fetchall()
        for title, company, sal, raw in samples:
            print(f"        - {title} @ {company}: {sal:.0f} CZK (raw: {raw})")

    # Salary distribution
    salary_stats = conn.execute("""
        SELECT
            MIN(avg_salary) as min_sal,
            AVG(avg_salary) as avg_sal,
            MAX(avg_salary) as max_sal
        FROM signals
        WHERE avg_salary > 0
    """).fetchone()
    print(f"\nSalary Range: {salary_stats[0]:.0f} - {salary_stats[2]:.0f} CZK")
    print(f"Average: {salary_stats[1]:.0f} CZK")

    # Test 2: City Data Quality
    print("\n" + "─" * 70)
    print("🌍 TEST 2: CITY/LOCATION QUALITY")
    print("─" * 70)

    city_stats = conn.execute("""
        SELECT city, COUNT(*) as cnt
        FROM signals
        GROUP BY city
        ORDER BY cnt DESC
        LIMIT 15
    """).fetchall()

    print(f"Top 15 Cities:")
    suspicious_cities = []
    for city, cnt in city_stats:
        pct = (cnt / total_jobs) * 100
        print(f"  {city:30s} {cnt:5,} ({pct:5.1f}%)")

        # Flag suspicious patterns
        if len(city) > 50:
            suspicious_cities.append(f"{city} (too long)")
        if city == "Unknown Employer":
            suspicious_cities.append(f"{city} (wrong field?)")

    if suspicious_cities:
        print(f"\n❌ FAIL: Found suspicious city names:")
        for s in suspicious_cities:
            print(f"     - {s}")
    else:
        print(f"\n✅ PASS: No obviously corrupted city names detected")

    # Test 3: Company Names
    print("\n" + "─" * 70)
    print("🏢 TEST 3: COMPANY NAME QUALITY")
    print("─" * 70)

    # Check for bullet characters in company names (corruption indicator)
    with_bullets = conn.execute("""
        SELECT COUNT(*)
        FROM signals
        WHERE company LIKE '%•%' OR company LIKE '%▪%'
    """).fetchone()[0]

    bullet_pct = (with_bullets / total_jobs) * 100
    status_bullets = "✅ PASS" if bullet_pct < 1 else "❌ FAIL"
    print(f"{status_bullets} Companies with bullet chars: {with_bullets} ({bullet_pct:.2f}%)")

    # Unknown employers
    unknown = conn.execute("SELECT COUNT(*) FROM signals WHERE company = 'Unknown Employer'").fetchone()[0]
    unknown_pct = (unknown / total_jobs) * 100
    status_unknown = "✅ PASS" if unknown_pct < 5 else "⚠️  WARN"
    print(f"{status_unknown} Unknown employers: {unknown} ({unknown_pct:.2f}%)")

    # Very short company names (likely corrupted)
    too_short = conn.execute("SELECT COUNT(*) FROM signals WHERE LENGTH(company) <= 2").fetchone()[0]
    short_pct = (too_short / total_jobs) * 100
    status_short = "✅ PASS" if short_pct < 1 else "❌ FAIL"
    print(f"{status_short} Suspiciously short names (≤2 chars): {too_short} ({short_pct:.2f}%)")

    # Test 4: Description Quality
    print("\n" + "─" * 70)
    print("📝 TEST 4: DESCRIPTION QUALITY")
    print("─" * 70)

    empty_desc = conn.execute("SELECT COUNT(*) FROM signals WHERE description IS NULL OR description = ''").fetchone()[0]
    empty_pct = (empty_desc / total_jobs) * 100
    status_desc = "✅ PASS" if empty_pct < 10 else "⚠️  WARN"
    print(f"{status_desc} Empty descriptions: {empty_desc} ({empty_pct:.2f}%)")

    avg_length = conn.execute("SELECT AVG(LENGTH(description)) FROM signals WHERE description IS NOT NULL").fetchone()[0]
    print(f"Average description length: {avg_length:.0f} characters")

    # Very short descriptions (likely extraction errors)
    too_short_desc = conn.execute("SELECT COUNT(*) FROM signals WHERE LENGTH(description) < 100 AND description IS NOT NULL").fetchone()[0]
    short_desc_pct = (too_short_desc / (total_jobs - empty_desc)) * 100 if (total_jobs - empty_desc) > 0 else 0
    status_short_desc = "✅ PASS" if short_desc_pct < 5 else "⚠️  WARN"
    print(f"{status_short_desc} Suspiciously short descriptions (<100 chars): {too_short_desc} ({short_desc_pct:.2f}%)")

    # Test 5: NULL Analysis
    print("\n" + "─" * 70)
    print("🔍 TEST 5: NULL/MISSING DATA ANALYSIS")
    print("─" * 70)

    null_stats = conn.execute("""
        SELECT
            COUNT(*) FILTER (WHERE salary_raw IS NULL) as null_salary,
            COUNT(*) FILTER (WHERE description IS NULL OR description = '') as null_desc,
            COUNT(*) FILTER (WHERE city IS NULL OR city = '') as null_city
        FROM signals
    """).fetchone()

    print(f"NULL Salary: {null_stats[0]:,} ({null_stats[0]/total_jobs*100:.1f}%)")
    print(f"NULL Description: {null_stats[1]:,} ({null_stats[1]/total_jobs*100:.1f}%)")
    print(f"NULL City: {null_stats[2]:,} ({null_stats[2]/total_jobs*100:.1f}%)")

    # Overall Quality Score
    print("\n" + "=" * 70)
    print("📊 OVERALL DATA QUALITY SCORE")
    print("=" * 70)

    issues = []
    if too_low_pct >= 5:
        issues.append(f"High suspicious-low salaries: {too_low_pct:.1f}%")
    if too_high_pct >= 1:
        issues.append(f"High suspicious-high salaries: {too_high_pct:.1f}%")
    if suspicious_cities:
        issues.append(f"Corrupted city names: {len(suspicious_cities)}")
    if bullet_pct >= 1:
        issues.append(f"Bullet chars in companies: {bullet_pct:.1f}%")
    if empty_pct >= 10:
        issues.append(f"High empty descriptions: {empty_pct:.1f}%")

    if not issues:
        print("✅ EXCELLENT: No critical data quality issues detected!")
        print(f"   Estimated Data Quality: 95-99%")
    elif len(issues) <= 2:
        print("⚠️  GOOD: Minor data quality issues detected")
        print(f"   Estimated Data Quality: 90-95%")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("❌ POOR: Multiple data quality issues detected")
        print(f"   Estimated Data Quality: 80-90%")
        for issue in issues:
            print(f"   - {issue}")

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")
    print("=" * 70)

    if too_low_pct >= 5:
        print("🔧 Fix hourly rate detection in analyzer.py line 317")
    if suspicious_cities:
        print("🔧 Fix city word boundary regex in scraper.py line 239")
    if bullet_pct >= 1:
        print("🔧 Fix company name cleaning in scraper.py line 211 (use re.sub not lstrip)")
    if too_high_pct >= 1:
        print("🔧 Fix decimal salary parsing in analyzer.py line 315")

    if not issues:
        print("✨ No fixes needed - data quality is excellent!")

    conn.close()

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Validation Complete")
print("=" * 70)
