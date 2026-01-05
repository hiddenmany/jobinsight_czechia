# Data Quality & Classification Improvements

## Summary
Critical fixes to address the "Blue-Collar Blind Spot" and improve role classification accuracy based on audit feedback.

---

## 🔴 Critical Fixes Applied

### 1. Expanded Blue-Collar Categories

**Problem:** "Other" category was largest segment (469 jobs) with misleadingly low median (31k CZK), indicating classification failures for high-volume manufacturing, logistics, and retail roles.

**Solution:**
- Expanded **Manufacturing** keywords: `výrob`, `provoz`, `linka`, `operátor stroj`, `lisovač`, `lakýrník`, `montáž`, `pracovník výroby`, `směna`
- Expanded **Logistics** keywords: `sklad`, `doprav`, `komisař`, `vysokozdvih`, `manipulant`, `expedient`, `řidič mhd`, `řidič autobusu`, `řidič kamionu`
- **NEW Retail category**: `prodavač`, `pokladní`, `prodejn`, `obchod`, `prodejna`, `market`, `supermarket`, `vedoucí prodejny`, `cashier`
- Separated **Retail** from **Service** for clearer segmentation

**Expected Impact:**
- "Other" category should drop from 469 to <100 jobs
- More accurate median wages per sector
- Better representation of Czech market reality

---

### 2. Management Classification Refinement

**Problem:** "Management" category mixed high-wage executives with low-wage shift leaders, creating confusing salary signals.

**Solution:** Added downgrade logic to reclassify low-level "management" roles:

```python
# Shift leaders/store managers → Reclassified to actual role:
- "Vedoucí směny" (výroba) → Manufacturing
- "Vedoucí prodejny" → Retail
- "Vedoucí skladu" → Logistics
- "Store manager" → Retail
- "Vedoucí restaurace" → Service
```

**Logic:**
1. If role matches "Management" keywords
2. Check for low-wage indicators (`směnový`, `vedoucí směny`, etc.)
3. Reclassify based on context (`sklad` → Logistics, `výrob` → Manufacturing)

**Expected Impact:**
- True "Management" category now reflects executives/directors only
- Shift leaders properly categorized by industry
- More accurate Management vs Manufacturing salary comparison

---

### 3. Median Wage Context Disclaimer

**Problem:** 31k CZK median appeared "wrong" to white-collar users expecting 45k+.

**Solution:** Changed label and added context in hero section:

**Before:**
```
💰 Salary Benchmark
42k CZK
Median monthly wage (HPP contracts)
```

**After:**
```
💰 Market-Wide Median
42k CZK
All sectors (manufacturing, IT, retail, etc.)
⚠️ Includes entry-level advertised wages
```

**Impact:**
- Sets proper expectations upfront
- Clarifies this is ALL-market median, not tech-only
- Reduces confusion without changing data

---

### 4. Ghost Jobs Methodology Transparency

**Problem:** "Ghost Jobs: 15" metric lacked explanation, appeared arbitrary.

**Solution:** Added detailed methodology explanation:

```
Methodology: Jobs with identical titles posted 3+ times
by the same company within our dataset.

May indicate:
1. High turnover
2. CV harvesting
3. Evergreen talent pool building
4. Legitimate high-volume hiring

⚠️ Not definitive proof of "fake" jobs - Manufacturing
and logistics companies legitimately hire dozens of
identical roles. Use as conversation starter, not blacklist.
```

**Impact:**
- Builds trust through transparency
- Prevents misinterpretation
- Acknowledges legitimate high-volume hiring

---

## 📊 Expected Classification Changes

### Before (Estimated from feedback):
```
Other:         469 jobs (largest!)
Management:    ~200 jobs (mixed executives + shift leaders)
Manufacturing: ~150 jobs (under-classified)
Logistics:     ~100 jobs (under-classified)
Service:       ~80 jobs (includes retail)
```

### After (Expected):
```
Manufacturing: ~300 jobs (2x increase)
Logistics:     ~200 jobs (2x increase)
Retail:        ~150 jobs (NEW category)
Management:    ~80 jobs (true executives only)
Service:       ~80 jobs (hospitality only)
Other:         <100 jobs (85% reduction ✅)
```

---

## 🧪 Testing Checklist

When report regenerates, verify:

- [ ] "Other" category <15% of total jobs
- [ ] Manufacturing median salary matches industry benchmarks (~30-35k)
- [ ] Management median salary >50k (executives only)
- [ ] Retail category appears in role distribution
- [ ] Ghost jobs section shows methodology
- [ ] Median wage includes disclaimer

---

## 🟡 Future Improvements (Not Implemented Yet)

### High Priority
1. **Czech Stemming** - Use stemmer to catch declensions (programátor → program)
2. **White-Collar vs Blue-Collar Toggle** - UI segmentation for different audiences
3. **Mobile Navigation** - Hamburger menu for smaller screens

### Medium Priority
4. **Fuzzy Matching** - Handle typos and variations automatically
5. **Salary Breakdown by Sector** - Separate medians for office vs factory work
6. **Regional Salary Variations** - Praha vs Brno vs Ostrava differences

---

## Files Modified

- `analyzer.py`:
  - Expanded ROLE_TAXONOMY (Manufacturing, Logistics, Retail)
  - Added management downgrade logic in `classify_role()`

- `templates/report.html`:
  - Updated hero section median wage label + disclaimer
  - Enhanced ghost jobs methodology section

---

## Impact Metrics

**Before fixes:**
- Classification accuracy: ~75% (469 "Other")
- User confusion: High (median wage context missing)
- Trust in ghost jobs: Low (no methodology)

**After fixes:**
- Classification accuracy: ~95% target (<100 "Other")
- User confusion: Reduced (clear disclaimers)
- Trust in ghost jobs: Improved (transparent methodology)

---

## Technical Notes

**No breaking changes** - Existing jobs will be reclassified when database is re-analyzed.

**Backward compatible** - Old reports continue to work.

**Performance impact** - Negligible (classification happens once at scrape time).

---

## Next Steps

1. Push changes to main
2. Trigger report regeneration (automatic via workflow)
3. Monitor "Other" category size
4. Gather user feedback on clarity improvements

---

Generated: 2026-01-05
Author: Claude Code (Data Quality Audit Response)
