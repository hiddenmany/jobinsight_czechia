# GitHub Actions Workflows

## Architecture

This project uses a **two-workflow strategy** to separate expensive scraping from fast report updates:

### 1. `weekly_scrape.yml` - Full Scrape (3+ hours)
**Triggers:**
- Schedule: Every Monday at 8:00 AM UTC
- Manual: "Run workflow" button in GitHub Actions

**What it does:**
1. Scrapes all job sites (Jobs.cz, Prace.cz, StartupJobs, WTTJ, Cocuma)
2. Updates database (`data/intelligence.db` via Git LFS)
3. Generates reports (`public/index.html`, etc.)
4. Commits everything with `[skip ci]` tag
5. Deploys to GitHub Pages

**Runtime:** ~3-4 hours (conservative scraping with rate limit cooldowns)

---

### 2. `update_report.yml` - Report Only (~2 minutes)
**Triggers:**
- Push to `main` branch (only for specific files):
  - `generate_report.py`
  - `visualizer.py`
  - `analyzer.py`
  - `templates/**`
  - `config/**`
- Manual: "Run workflow" button

**What it does:**
1. Pulls existing database from Git LFS (no scraping)
2. Regenerates reports from existing data
3. Commits updated reports with `[skip ci]` tag
4. Deploys to GitHub Pages

**Runtime:** ~2 minutes

---

## Usage Scenarios

### Scenario 1: Weekly Scrape (Automatic)
- **When:** Every Monday 8am UTC
- **Action:** None required, runs automatically
- **Result:** Fresh data + updated reports

### Scenario 2: Fix Report Bug or Update Template
- **When:** You modify `generate_report.py`, templates, or config
- **Action:** Push changes to main branch
- **Result:** `update_report.yml` runs automatically (fast)
- **Database:** Unchanged, uses existing scraped data

### Scenario 3: Manual Scrape (Emergency)
- **When:** Need fresh data before Monday
- **Action:** Go to Actions → Weekly Job Scraper → "Run workflow"
- **Result:** Full scrape + report update

### Scenario 4: Local Development
```bash
# Work on reports locally without scraping
python generate_report.py
python visualizer.py

# Push changes - triggers update_report.yml only
git add generate_report.py public/
git commit -m "fix: improve salary visualization"
git push
```

---

## Preventing Infinite Loops

Both workflows use `[skip ci]` in commit messages to prevent triggering each other:
- `weekly_scrape.yml` commits: `"Auto-update: Job market data [date] [skip ci]"`
- `update_report.yml` commits: `"chore: regenerate reports [skip ci]"`

This ensures:
- Scraper commits don't trigger report updates
- Report commits don't trigger more report updates

---

## Database Persistence

The database (`data/intelligence.db`) is stored in **Git LFS**:
- Survives between workflow runs
- ~40-70 MB size
- 14-day job retention policy
- Automatic VACUUM compaction

**LFS Bandwidth:** ~100-150 MB/month (well under 1GB free tier)

---

## Monitoring

Check workflow status:
- GitHub Actions tab: See run history
- `App_Health.md`: Manual health checks
- Logs: Each workflow logs database stats and scraping metrics
