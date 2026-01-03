# Czechia Localization Audit Report

## Summary
The JobsCzInsight application has **bilingual support (English + Czech)** with generally good coverage. However, there are some inconsistencies and missing localizations.

## ✅ What Works Well

### 1. **Dual Report Generation**
- `generate_report.py` correctly generates both English and Czech versions
- Templates: `report.html` (EN) and `report_cz.html` (CZ)
- Output: `public/index.html` (EN) and `public/index_cz.html` (CZ)
- Czech date formatting with proper month names (ledna, února, etc.)

### 2. **Data Sources Configuration**
- `config/selectors.yaml` properly targets Czech market:
  - WTTJ: `?aroundQuery=Czechia`
  - LinkedIn: `location=Czechia`
- Czech city names in fallback_cities config

### 3. **Taxonomy & Analysis**
- `analyzer.py` includes both Czech and English keywords:
  - Role keywords: 'programátor', 'vývojář', 'developer', 'engineer'
  - Seniority: 'zkušený', 'absolvent', 'vedoucí'
  - Contract: 'HPP', 'IČO', 'Brigáda'

## ⚠️ Issues Found

### 1. **Inconsistent Location Labels**
**File: analyzer.py**
- Line 103: `location: str = "CZ"` - Uses "CZ" as default
- Line 209: Returns `"CZ"` when city detection fails

**Issue**: Should use "Czechia" or "Czech Republic" for consistency with LinkedIn/WTTJ

**Fix Needed**:
```python
location: str = "Czechia"  # Line 103
return "Czechia"  # Line 209
```

### 2. **Mixed Language in Code**
**File: scraper.py**
- English comments and docstrings (good for maintainability)
- Czech selectors (`:has-text('Praha')`, `:has-text('Brno')`)
- Button text: `"Přijmout"`, `"Zobrazit více"`, `"Číst dál"` (Czech only)

**Status**: Acceptable - code is English, UI detection is localized

### 3. **Hardcoded Czech-Only Patterns**
**File: config/selectors.yaml**
- Read more buttons only in Czech: `"Zobrazit více"`, `"Číst dál"`
- Missing English equivalents: `"Show more"`, `"Read more"` (partially covered)

**Fix Needed**: Add both Czech and English button patterns

### 4. **Logging Messages**
**File: scraper.py**
- All logging is in English only
- Example: `"Skipping {site_name} - circuit breaker is open"`

**Status**: Acceptable - logs are typically in English for developer tools

### 5. **README Documentation**
**File: README.md**
- Entirely in English
- No Czech version exists

**Recommendation**: Create `README_CZ.md` for Czech users

## 📋 Localization Coverage Matrix

| Component | English | Czech | Notes |
|-----------|---------|-------|-------|
| HTML Reports | ✅ | ✅ | Both templates exist |
| Data Analysis | ✅ | ✅ | Bilingual keywords |
| Scraper Config | ✅ | ✅ | Targets CZ market |
| Logging | ✅ | ❌ | English only (acceptable) |
| README | ✅ | ❌ | No Czech version |
| Code Comments | ✅ | ❌ | English only (best practice) |
| Location Labels | ⚠️ | ⚠️ | Inconsistent "CZ" vs "Czechia" |

## 🔧 Recommended Fixes

### Priority 1 (Critical)
1. **Standardize location labels**: Change "CZ" to "Czechia" throughout analyzer.py
2. **Add missing button patterns**: Include English "Show more", "Read more" variants

### Priority 2 (Nice to Have)
3. **Create README_CZ.md**: Czech version of documentation
4. **Add language switcher**: Link between EN/CZ versions in HTML reports

### Priority 3 (Optional)
5. **Bilingual error messages**: Add Czech translations for user-facing errors
6. **Config documentation**: Add Czech comments in selectors.yaml

## ✅ Conclusion

**Overall Grade: B+**

The application has **strong bilingual support** for its primary function (reports and analysis). The main issues are:
- Inconsistent location labels ("CZ" vs "Czechia")
- Missing Czech README

The localization strategy is **appropriate** for a developer tool with Czech market focus:
- User-facing content: Bilingual ✅
- Code/logs: English (industry standard) ✅  
- Data analysis: Czech-aware ✅

**Recommendation**: Apply Priority 1 fixes for production readiness.
