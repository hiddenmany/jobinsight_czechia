# HR Specialist & Employer Value Analysis

## Executive Summary

**Overall Value: 6.5/10** - Useful but with significant gaps

The data provides good **market-level insights** but lacks the **granular detail** 
that HR specialists and employers need for compensation planning and talent strategy.

---

## STRENGTHS (What's Valuable) ✅

### 1. **Market Salary Benchmarking** (Value: HIGH)
**Current Data:**
- Median: 40,000 CZK
- P25: 32,500 CZK  
- P75: 49,000 CZK
- 44% of jobs have salary data (3,140/7,131)

**HR Value:**
- ✅ Helps employers set competitive salary ranges
- ✅ Shows market percentiles for positioning
- ✅ Platform-specific insights (StartupJobs: 110k vs Prace.cz: 39k)

**Limitations:**
- ❌ Only 44% coverage (56% missing salary data)
- ❌ No breakdown by role type (developer vs sales vs admin)
- ❌ No seniority levels (junior vs senior vs lead)
- ❌ No skill-based premium analysis

---

### 2. **Tech Stack Trends** (Value: MEDIUM-HIGH)
**Current Data:**
- Modern: 46% (3,292 jobs)
- Stable: 53% (3,832 jobs)
- Dinosaur: 0% (7 jobs - nearly extinct!)

**HR Value:**
- ✅ Shows which companies are adopting modern tech
- ✅ Identifies tech debt risk in market
- ✅ Helps plan hiring strategy

**Limitations:**
- ❌ Binary classification (can't see which specific techs are hot)
- ❌ No correlation with salary (which techs pay premium?)
- ❌ No trend data (is Modern % increasing over time?)

---

### 3. **Contract Type Reality** (Value: MEDIUM)
**Current Data:**
- HPP (full-time): 94%
- IČO (contractors): 3%
- Brigáda (part-time): 1%

**HR Value:**
- ✅ Shows market preference for full-time
- ✅ Identifies contractor opportunities (low but present)

**Limitations:**
- ❌ No salary differential between contract types
- ❌ Missing DPP/DPČ distinction
- ❌ No benefits comparison

---

### 4. **Source Distribution** (Value: LOW-MEDIUM)
**Current Data:**
- Prace.cz: 5,594 jobs (79%)
- Jobs.cz: 945 jobs (13%)
- StartupJobs: 500 jobs
- Others: <50 jobs each

**HR Value:**
- ✅ Shows where to post jobs for maximum visibility
- ✅ Reveals platform-specific salary expectations

**Limitations:**
- ❌ Not actionable (employers already know where to post)
- ❌ No quality metrics (views per posting, applicant quality)

---

## CRITICAL GAPS (What's Missing) ❌

### 1. **Role-Specific Salary Data** (CRITICAL GAP)
**What's Missing:**
- No breakdown by: Developer, Sales, HR, Marketing, Operations, etc.
- No seniority levels: Junior (0-2 yrs), Mid (3-5 yrs), Senior (6+ yrs), Lead (10+ yrs)
- No skill premiums: React vs Angular, AWS vs Azure, etc.

**Why HR Needs This:**
- Can't use 40k median to price a Senior Developer (should be 80-120k)
- Can't compare apples to apples

**Fix Complexity:** MEDIUM
- Need NLP to extract seniority from titles ("Junior", "Senior", "Lead")
- Need role classification ("Developer", "Designer", "Analyst")
- ~200 lines of code

---

### 2. **Geographic Salary Differences** (HIGH GAP)
**Current State:**
- 99% of jobs show "CZ" (no city)
- Only 35 jobs (0.5%) have actual cities

**What's Missing:**
- Praha vs Brno vs Ostrava salary differences (typically 20-30% premium in Praha)
- Regional hiring hotspots
- Commute vs remote correlation

**Why HR Needs This:**
- Location-based compensation planning
- Office location strategy
- Talent pool identification

**Fix Status:** IN PROGRESS (v18 improved city extraction to 38% on fresh data)
- Need 1-2 more scrapes to build up city dataset
- Current data is mostly pre-v17 (no cities)

---

### 3. **Benefit Package Intelligence** (MEDIUM GAP)
**Current Approach:**
- Keyword counting ("multisport", "sick day", etc.)
- Binary presence/absence

**What's Missing:**
- No benefit value estimation (5 days vacation vs 25 days)
- No benefit bundles (common combinations)
- No correlation with salary (higher salary = fewer benefits?)

**Why HR Needs This:**
- Total compensation planning
- Competitive positioning
- Benefit optimization

**Fix Complexity:** HIGH (needs structured benefit extraction)

---

### 4. **Time-Series Trends** (HIGH GAP)
**Current State:**
- Single snapshot (weekly)
- No historical comparison
- No trend analysis

**What's Missing:**
- Week-over-week salary changes
- Hiring velocity (companies ramping up/down)
- Emerging skills tracking
- Seasonal patterns

**Why HR Needs This:**
- Identify hiring windows
- Track compensation inflation
- Spot emerging competitors

**Fix Complexity:** MEDIUM
- Data is being collected (scraped_at, last_seen_at)
- Just need visualization layer
- ~300 lines of code for trend charts

---

### 5. **Company-Specific Intelligence** (MEDIUM GAP)
**Current State:**
- Top Innovators table (hiring volume only)
- No company profiles
- No reputation data

**What's Missing:**
- Company growth rate (hiring velocity)
- Employer reputation score (toxicity, tech stack, salary)
- Benefit offerings per company
- Competitor analysis (who's hiring for same roles)

**Why HR Needs This:**
- Competitive intelligence
- Poaching risk assessment
- Employer branding strategy

**Fix Complexity:** MEDIUM-HIGH

---

### 6. **Skills Demand Analysis** (HIGH GAP)
**Current State:**
- Tech stack classification (Modern/Stable/Dinosaur)
- No specific skill tracking

**What's Missing:**
- Which skills are most in-demand? (React: 500 jobs, Python: 800 jobs, etc.)
- Skill combinations (React + TypeScript + AWS)
- Skill salary premiums (Kubernetes adds 15k to salary)
- Emerging skills (trending up)

**Why HR Needs This:**
- Training program planning
- Hiring strategy prioritization
- Compensation benchmarking per skill

**Fix Complexity:** MEDIUM (NLP-based skill extraction)

---

### 7. **Employer Branding Insights** (LOW-MEDIUM GAP)
**Current State:**
- Toxicity score exists but not exposed
- No reputation ranking

**What's Missing:**
- "Best places to work" ranking
- Culture indicators (agile, remote-first, etc.)
- Work-life balance signals
- Growth opportunity indicators

**Why HR Needs This:**
- Positioning strategy
- Talent attraction messaging
- Competitive differentiation

**Fix Complexity:** MEDIUM

---

## DATA QUALITY ASSESSMENT FOR HR USE

### Salary Data: 6/10
- ✅ Good: Market medians, percentiles, platform comparison
- ❌ Missing: Role-specific, seniority-based, skill-based, geographic
- **Verdict**: Useful for broad market sense, insufficient for specific roles

### Geographic Data: 2/10  
- ❌ 99% show "CZ" (useless for location strategy)
- ✅ v18 improves to 38% on fresh data (needs more scrapes)
- **Verdict**: Currently not useful, will improve with next scrape

### Contract Intelligence: 7/10
- ✅ Shows HPP dominance (94%)
- ✅ Tracks IČO and Brigáda trends
- ❌ No salary differential analysis
- **Verdict**: Good high-level view

### Remote Work: 5/10
- ✅ Shows 8% remote availability (realistic for Czech market)
- ❌ No hybrid vs full-remote distinction
- ❌ No correlation with salary or tech stack
- **Verdict**: Basic but useful

### Language Requirements: 4/10
- ⚠️ Only 4% English-friendly (seems low, may be detection issue)
- ❌ No language premium analysis
- **Verdict**: Questionable accuracy, needs validation

### Tech Stack: 7/10
- ✅ Modern vs Legacy classification works well
- ✅ Shows 46% Modern adoption (positive signal)
- ❌ No specific technology demand breakdown
- **Verdict**: Good strategic view, lacks tactical detail

### Company Intelligence: 5/10
- ✅ Top Innovators identified (Modern tech adopters)
- ❌ No hiring velocity, growth rate, or reputation
- **Verdict**: Surface-level insights only

---

## ACTIONABLE VALUE FOR DIFFERENT PERSONAS

### For HR Specialists:
**Current Value: 5/10**

**What They Can Use:**
- ✅ Market salary ranges for budgeting
- ✅ Contract type trends
- ✅ Remote work prevalence
- ✅ Tech stack expectations

**What They Can't Use:**
- ❌ Role-specific salary benchmarks
- ❌ Competitor hiring analysis
- ❌ Skill demand forecasting
- ❌ Geographic compensation differences

**Bottom Line**: Good for executive summary, insufficient for hiring plan details.

---

### For Employers/Hiring Managers:
**Current Value: 6/10**

**What They Can Use:**
- ✅ Competitive salary positioning
- ✅ Tech stack competitive analysis
- ✅ P
