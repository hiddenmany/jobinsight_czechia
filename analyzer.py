import pandas as pd
import re
import os
import numpy as np
from collections import Counter

def remove_outliers(df, column='avg_salary', sigma=3):
    if df.empty or column not in df.columns: return df
    valid_data = df[df[column] > 0].dropna(subset=[column])
    if valid_data.empty: return df
    mean, std = valid_data[column].mean(), valid_data[column].std()
    lower, upper = mean - (sigma * std), mean + (sigma * std)
    return df[(df[column] >= lower) & (df[column] <= upper) | (df[column].isna())]

def parse_salary_info(salary_str):
    if not isinstance(salary_str, str): return None, None, None
    s = salary_str.lower().replace('\xa0', '').replace(' ', '').replace('.', '') # Remove dots too
    is_yr = any(x in s for x in ['ročně', 'rok', 'year', 'annual'])
    is_hr = any(x in s for x in ['hod', '/h', 'hour'])
    rate = 25.0 if any(x in s for x in ['eur', '€']) else 1.0
    nums = [int(n) for n in re.findall(r'(\d+)', s)]
    if not nums: return None, None, None
    nums.sort()
    if not is_hr: nums = [n for n in nums if n >= 100 and not (2020 <= n <= 2030)]
    else: nums = [n for n in nums if n >= 50]
    if not nums: return None, None, None
    v_min, v_max = nums[0] * rate, nums[-1] * rate
    if is_hr: v_min, v_max = v_min * 160, v_max * 160
    elif is_yr or v_max > 250000: v_min, v_max = v_min / 12, v_max / 12
    return v_min, v_max, (v_min + v_max) / 2

class MarketIntelligence:
    def __init__(self):
        self.df = self.load_all_data()
        if self.df.empty:
            self.history = pd.DataFrame()
            self.istyle = pd.DataFrame()
            self.market = pd.DataFrame()
        else:
            self.df = self.df.sort_values('scraped_at', ascending=False).drop_duplicates(subset=['link'], keep='first')
            self.history = self.df.copy() # Simplified for this snapshot
            self.history['date'] = pd.to_datetime(self.history['scraped_at']).dt.date
            
            # iSTYLE FOCUS: Praha, Brno, Ostrava, Ústí nad Labem
            target_cities = ['Praha', 'Brno', 'Ostrava', 'Ústí nad Labem']
            self.istyle = self.df[self.df['company'].str.contains('iSTYLE', case=False, na=False) & self.df['city'].isin(target_cities)]
            self.market = self.df[~self.df['company'].str.contains('iSTYLE', case=False, na=False)]

    def load_all_data(self):
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        if not os.path.exists(data_dir): return pd.DataFrame()
        dfs = []
        for f in os.listdir(data_dir):
            if f.endswith('.csv'):
                try:
                    tmp = pd.read_csv(os.path.join(data_dir, f))
                    tmp['source'] = f.split('.')[0].capitalize()
                    dfs.append(tmp)
                except: continue
        if not dfs: return pd.DataFrame()
        df = pd.concat(dfs, ignore_index=True)
        
        # Salary Parsing
        stats = df['salary'].apply(parse_salary_info)
        df['min_salary'], df['max_salary'], df['avg_salary'] = zip(*stats)
        df = remove_outliers(df, 'avg_salary')
        
        # Basic Cleaning
        df['city'] = df['location'].astype(str).apply(lambda x: x.split('–')[0].split('-')[0].split(',')[0].strip())
        df['category'] = df.apply(self.categorize, axis=1)
        
        if 'atmoskop_count' not in df.columns:
            df['atmoskop_count'] = 0
        df['atmoskop_count'] = pd.to_numeric(df['atmoskop_count'], errors='coerce').fillna(0)
        return df

    def categorize(self, row):
        t = str(row.get('title', '')).lower()
        rules = {
            'IT a technologie': ['developer', 'sw', 'it ', 'data', 'analytik'],
            'Management': ['ředitel', 'manager', 'lead', 'head of', 'vedoucí'],
            'Retail Sales (Expert)': ['rse', 'prodej', 'sales', 'expert', 'konzultant'],
            'Logistika': ['sklad', 'logistik', 'řidič']
        }
        for cat, kws in rules.items():
            if any(k in t for k in kws): return cat
        return 'Ostatní'

    def get_market_sentiment(self):
        if self.df.empty: return {"Median Market Wage": "N/A", "Transparency Score": "0%"}
        med = self.df[self.df['avg_salary'] > 0]['avg_salary'].median()
        transp = (self.df[self.df['avg_salary'] > 0].shape[0] / len(self.df)) * 100
        return {
            "Median Market Wage": f"{int(med):,} CZK" if pd.notna(med) else "N/A",
            "Vacancy Pressure": "High" if len(self.df) > 1000 else "Moderate",
            "Transparency Score": f"{int(transp)}%",
            "Leading Sector": self.df['category'].value_counts().idxmax()
        }

    def get_deep_content_insights(self):
        if self.df.empty or 'description' not in self.df.columns: 
            return {"Academy Prevalence": "0%", "Market Focus": "N/A"}
        desc = self.df['description'].fillna('').str.lower()
        acad = sum(1 for d in desc if any(k in d for k in ['akademie', 'academy', 'trénink']))
        return {
            "Academy Prevalence": f"{int((acad/max(len(desc),1))*100)}%",
            "Market Focus": "Learning-Heavy" if (acad/max(len(desc),1)) > 0.15 else "Requirement-Heavy"
        }

    def get_competitor_duel(self, rival_name):
        rival = self.df[self.df['company'].str.contains(re.escape(rival_name), case=False, na=False)]
        if rival.empty: return None
        def st(d):
            return {
                "avg_sal": d['avg_salary'].median(),
                "transp": (d['avg_salary']>0).sum()/max(len(d),1)*100,
                "academy": d['description'].fillna('').str.contains('akademie', case=False).sum()/max(len(d),1)*100
            }
        return {"istyle": st(self.istyle), "rival": st(rival), "metric_names": ["Medián mzdy", "Transparentnost (%)", "Důraz na vzdělávání (%)"]}

    def get_tactical_counter_strike(self, rival_name):
        return ["Akcentovat Apple certifikaci", "Zrychlit proces na 24h", "Uvést mzdové rozmezí"]

    def get_geo_intel(self):
        if self.df.empty: return pd.DataFrame()
        return self.df.groupby('city').size().reset_index(name='Volume').sort_values('Volume', ascending=False)

    def get_reputation_map(self):
        if self.df.empty: return pd.DataFrame()
        return self.df[self.df['company'] != 'Unknown'].groupby('company').agg({'atmoskop_count': 'max', 'title': 'count', 'avg_salary': 'median'}).rename(columns={'title': 'Active Jobs', 'avg_salary': 'Median Salary'}).reset_index()

    def get_jd_health_score(self, description):
        if not description: return 0
        d = str(description).lower(); s = 0
        if any(k in d for k in ['nabízíme', 'benefity']): s += 25
        if any(k in d for k in ['učit', 'rozvoj', 'akademie']): s += 25
        if any(k in d for k in ['hybrid', 'home office']): s += 25
        if any(k in d for k in ['požadujeme', 'očekáváme']): s += 25
        return s

    def get_cai_score(self, row):
        return 75 if pd.notna(row.get('avg_salary')) else 45

    def get_regional_data(self):
        region_map = {'Praha': 'Praha', 'Brno': 'Jihomoravský', 'Ostrava': 'Moravskoslezský', 'Ústí nad Labem': 'Ústecký'}
        df_reg = self.df.copy()
        df_reg['Region'] = df_reg['city'].map(region_map).fillna('Ostatní regiony')
        return df_reg.groupby('Region').size().reset_index(name='Pozice')

    def get_market_vibe(self):
        vk = {'Inovace': ['moderní', 'technologie'], 'Stabilita': ['jistota', 'stabilní'], 'Tým': ['tým', 'přátelský'], 'Výkon': ['výsledky', 'cíle']}
        desc = " ".join(self.df['description'].fillna('').astype(str).head(100)).lower()
        res = {v: sum(1 for k in kws if k in desc) for v, kws in vk.items()}
        return pd.Series(res).sort_values(ascending=False)

    # --- 2026 STRATEGIC METRICS ---

    def get_ghost_job_index(self):
        """
        1. The Ghost Job & Desperation Index.
        Identifies high-frequency reposts suggesting churn or toxicity.
        """
        if self.df.empty: return pd.DataFrame()
        
        # In a real historical DB, we would count distinct scraped_at dates for the same (title, company).
        # Here we simulate 'Duplicates' based on strict title+company matches in the current snapshot
        # pretending they are reposts if we had history.
        # For this version, we find companies with many *similar* job titles.
        
        churn_stats = self.df.groupby('company')['title'].agg(['count', 'nunique']).reset_index()
        churn_stats['Ghost Score'] = churn_stats['count'] - churn_stats['nunique']
        # High Score = Reposting exact titles (or we captured multiple snapshots)
        return churn_stats.sort_values('Ghost Score', ascending=False).head(10)

    def get_contract_split(self):
        """
        2. IČO vs HPP Reality Check.
        """
        desc = self.df['description'].fillna('').astype(str).str.lower()
        
        ico_mask = desc.str.contains('ičo|faktur|freelance|contract', regex=True)
        hpp_mask = desc.str.contains('hpp|hlavní pracovní poměr|smlouv|zaměstnan', regex=True)
        
        return {
            "HPP (Employment)": hpp_mask.sum(),
            "IČO (Contract)": ico_mask.sum(),
            "Hybrid/Both": (ico_mask & hpp_mask).sum(),
            "Unspecified": len(desc) - (ico_mask | hpp_mask).sum()
        }

    def get_remote_truth(self):
        """
        3. The Remote Lie Detector.
        """
        desc = self.df['description'].fillna('').astype(str).str.lower()
        title = self.df['title'].fillna('').astype(str).str.lower()
        
        claimed_remote = title.str.contains('remote|home office|z domova', regex=True)
        
        # buried "onsite" keywords
        buried_office = desc.str.contains('kancelář|onsite|v sídle|docházk|office', regex=True)
        
        fake_remote = (claimed_remote & buried_office).sum()
        true_remote = (claimed_remote & ~buried_office).sum()
        
        return {
            "True Remote": true_remote,
            "Fake Remote (Bait)": fake_remote,
            "Office Only": len(desc) - (true_remote + fake_remote)
        }

    def get_tech_stack_lag(self):
        """
        4. Keyword Lag (The AI BS Filter).
        """
        desc = " ".join(self.df['description'].fillna('').astype(str)).lower()
        
        # 2026 Context
        modern = ['pytorch', 'llm', 'generative', 'fastapi', 'rust', 'go', 'react', 'next.js']
        legacy = ['jquery', 'angularjs', 'php 5', 'java 8', 'tensorflow', 'svn'] # TF is considered legacy vs PyTorch in this logic
        
        modern_counts = {k: desc.count(k) for k in modern}
        legacy_counts = {k: desc.count(k) for k in legacy}
        
        return {"Modern": modern_counts, "Legacy": legacy_counts}

    def get_language_barrier(self):
        """
        5. The English Tax.
        """
        desc = self.df['description'].fillna('').astype(str).str.lower()
        
        # Explicit Czech requirement
        cz_req_keywords = ['čeština', 'czech language', 'mluvíte česky', 'czech required', 'český jazyk']
        cz_req_mask = desc.apply(lambda x: any(k in x for k in cz_req_keywords))
        
        # Detect if text is English (Simple stopword heuristic)
        def is_english_text(text):
            en_stops = {'the', 'and', 'is', 'for', 'with', 'we', 'you'}
            cz_stops = {'je', 'pro', 'se', 'na', 'do', 've', 'o'}
            words = set(text.split())
            en_score = len(words.intersection(en_stops))
            cz_score = len(words.intersection(cz_stops))
            return en_score > cz_score

        is_english_mask = desc.apply(is_english_text)
        
        # English Friendly = (Written in English) AND (No explicit Czech requirement)
        en_friendly_mask = is_english_mask & ~cz_req_mask
        
        # Explicit English Only tag (keep for strictness)
        en_only_tag_mask = desc.str.contains('english only|en only', regex=True)
        
        final_en_mask = en_friendly_mask | en_only_tag_mask
        
        return {
            "Czech Required (Puddle)": cz_req_mask.sum(),
            "English Friendly (Ocean)": final_en_mask.sum(),
            "Flexible/Unknown": len(desc) - (cz_req_mask.sum() + final_en_mask.sum())
        }
