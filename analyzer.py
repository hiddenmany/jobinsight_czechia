import pandas as pd
import re
import os
import numpy as np
import hashlib
import unicodedata
from collections import Counter

def normalize_text(text):
    """Production-grade normalization for Czech character variants and white-space."""
    if not isinstance(text, str): return ""
    # Normalize unicode (NFKD) and handle Czech non-breaking spaces
    text = unicodedata.normalize('NFKD', text)
    text = text.replace('\u00a0', ' ').replace('\u202f', ' ')
    return text.strip()

def get_content_hash(row):
    """Generates a stable hash to detect reposted ads across different URLs."""
    content_str = f"{row.get('title', '')}{row.get('company', '')}{str(row.get('description', ''))[:500]}"
    clean_content = re.sub(r'\W+', '', content_str).lower()
    return hashlib.md5(clean_content.encode()).hexdigest()

def parse_salary_info(salary_str):
    """Robust salary parser handling space-separated thousands and currency variants."""
    if not isinstance(salary_str, str): return None, None, None
    
    # Normalize: "40 000" -> "40000", "40.000" -> "40000"
    s = normalize_text(salary_str).lower()
    s = s.replace(' ', '').replace('.', '').replace(',', '')
    
    is_yr = any(x in s for x in ['rocne', 'rok', 'year', 'annual'])
    is_hr = any(x in s for x in ['hod', '/h', 'hour'])
    rate = 25.0 if any(x in s for x in ['eur', '€']) else 1.0
    
    # Extract all digits
    nums = [int(n) for n in re.findall(r'(\d+)', s)]
    if not nums: return None, None, None
    nums.sort()
    
    # Filter out noise (like years 2024, 2025)
    if not is_hr:
        nums = [n for n in nums if n >= 1000 and not (2020 <= n <= 2030)]
    else:
        nums = [n for n in nums if n >= 50]
        
    if not nums: return None, None, None
    
    v_min, v_max = nums[0] * rate, nums[-1] * rate
    
    # Standardize to Monthly CZK
    if is_hr: 
        v_min, v_max = v_min * 160, v_max * 160
    elif is_yr or v_max > 300000: # Heuristic for annual/total packages
        v_min, v_max = v_min / 12, v_max / 12
        
    return float(v_min), float(v_max), float((v_min + v_max) / 2)

class DataManager:
    """Handles IO and Deduplication via Content Hashing."""
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def load_all(self):
        dfs = []
        for f in os.listdir(self.data_dir):
            if f.endswith('.csv'):
                try:
                    tmp = pd.read_csv(os.path.join(self.data_dir, f))
                    tmp['source'] = f.split('.')[0].capitalize()
                    dfs.append(tmp)
                except: continue
        if not dfs: return pd.DataFrame()
        df = pd.concat(dfs, ignore_index=True)
        
        # Apply Content Hash deduplication
        if not df.empty:
            df['content_hash'] = df.apply(get_content_hash, axis=1)
            df = df.sort_values('scraped_at', ascending=False).drop_duplicates(subset=['content_hash'])
        return df

class MarketIntelligence:
    def __init__(self):
        self.dm = DataManager()
        self.df = self.dm.load_all()
        
        if not self.df.empty:
            self._process_data()
        else:
            self.istyle = pd.DataFrame()

    def _process_data(self):
        # Apply strict parsing
        stats = self.df['salary'].apply(parse_salary_info)
        self.df['min_salary'], self.df['max_salary'], self.df['avg_salary'] = zip(*stats)
        
        # Clean City
        self.df['city'] = self.df['location'].astype(str).apply(
            lambda x: normalize_text(x).split('–')[0].split('-')[0].split(',')[0].strip()
        )
        
        target_cities = ['Praha', 'Brno', 'Ostrava', 'Usti nad Labem']
        self.istyle = self.df[self.df['company'].str.contains('iSTYLE', case=False, na=False)]

    def get_contract_split(self):
        desc = self.df['description'].fillna('').astype(str).str.lower()
        ico = desc.str.contains('ico|faktur|freelance|contract', regex=True).sum()
        hpp = desc.str.contains('hpp|hlavni pracovni pomer|smlouv|zamestnan', regex=True).sum()
        return {"HPP": hpp, "ICO": ico, "Other": len(desc) - (ico + hpp)}

    def get_remote_truth(self):
        desc = self.df['description'].fillna('').astype(str).str.lower()
        remote_kws = ['remote', 'z domova', 'plny remote', 'full remote']
        office_kws = ['kancelar', 'office', 'dochazka', 'onsite']
        
        is_remote = desc.apply(lambda x: any(k in x for k in remote_kws))
        has_office = desc.apply(lambda x: any(k in x for k in office_kws))
        
        true_remote = (is_remote & ~has_office).sum()
        fake_remote = (is_remote & has_office).sum()
        return {"True Remote": true_remote, "Hybrid/Fake": fake_remote, "Office": len(desc) - (true_remote+fake_remote)}

    def get_language_barrier(self):
        desc = self.df['description'].fillna('').astype(str).str.lower()
        def is_english(text):
            en_words = {'the', 'and', 'with', 'team', 'company'}
            words = set(text.split())
            return len(words.intersection(en_words)) > 2
        
        en_count = desc.apply(is_english).sum()
        return {"English Friendly": en_count, "Czech Only": len(desc) - en_count}

    def get_active_hashes(self):
        """Returns a set of all known content hashes in the current DB."""
        if self.df.empty or 'content_hash' not in self.df.columns: return set()
        return set(self.df['content_hash'].unique())

    def get_market_churn(self):
        """Calculates Velocity: How many jobs are stale vs fresh."""
        if self.df.empty: return {"New (7d)": 0, "Stale (>14d)": 0}
        
        self.df['scraped_at_dt'] = pd.to_datetime(self.df['scraped_at'], unit='s')
        now = pd.Timestamp.now()
        
        fresh = self.df[self.df['scraped_at_dt'] > (now - pd.Timedelta(days=7))].shape[0]
        stale = self.df[self.df['scraped_at_dt'] < (now - pd.Timedelta(days=14))].shape[0]
        
        return {"Fresh Signals": fresh, "Stale (Zombies)": stale}

    def get_market_vibe(self):
        desc = " ".join(self.df['description'].fillna('').astype(str).head(100)).lower()
        res = {
            'Innovation': desc.count('modern'),
            'Stability': desc.count('jistot') + desc.count('stabil'),
            'Performance': desc.count('vykon') + desc.count('vysledk')
        }
        return pd.Series(res).sort_values(ascending=False)