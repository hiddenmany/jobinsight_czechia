"""
LLM Market Analysis Module

Uses Google Gemini to generate weekly market insights from job data.
Falls back gracefully if API key is not available.
"""

import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def get_market_stats(df) -> Dict:
    """Extract key market statistics from the DataFrame for LLM analysis."""
    if df.empty:
        return {}
    
    # Basic counts
    total_jobs = len(df)
    
    # Role distribution (top 10)
    role_dist = df['role_type'].value_counts().head(10).to_dict()
    
    # Seniority distribution
    seniority_dist = df['seniority_level'].value_counts().to_dict()
    
    # Salary stats (only jobs with salary data)
    valid_sal = df[df['avg_salary'] > 0]
    salary_stats = {}
    if not valid_sal.empty:
        salary_stats = {
            'median': int(valid_sal['avg_salary'].median()),
            'count_with_salary': len(valid_sal),
            'percentage_with_salary': round(len(valid_sal) / total_jobs * 100, 1)
        }
        
        # Salary by role
        role_salary = valid_sal.groupby('role_type')['avg_salary'].median().sort_values(ascending=False).head(8)
        salary_stats['by_role'] = {k: int(v) for k, v in role_salary.items()}
    
    # Source distribution
    source_dist = df['source'].value_counts().to_dict()
    
    # Tech status
    tech_status = df['tech_status'].value_counts().to_dict() if 'tech_status' in df.columns else {}
    
    # Contract types (if available)
    contract_dist = {}
    if 'contract_type' in df.columns:
        contract_dist = df['contract_type'].value_counts().to_dict()
    
    # Top cities
    city_dist = df['city'].value_counts().head(5).to_dict() if 'city' in df.columns else {}
    
    return {
        'total_jobs': total_jobs,
        'role_distribution': role_dist,
        'seniority_distribution': seniority_dist,
        'salary_stats': salary_stats,
        'source_distribution': source_dist,
        'tech_status': tech_status,
        'contract_distribution': contract_dist,
        'top_cities': city_dist
    }


def generate_weekly_insights(stats: Dict, api_key: str) -> Dict:
    """
    Call Gemini API to generate market insights.
    
    Returns:
        Dict with keys: summary, key_insights (list), trend_alert (optional)
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')  # Gemini 2.5 Pro: best reasoning (GA)
        
        prompt = f"""# ROLE & EXPERTISE

Jsi seniorní analytik trhu práce a HR stratég s 15+ lety zkušeností v české ekonomice. Máš expertní znalosti v oblastech:
- Makroekonomických trendů českého pracovního trhu
- Kompenzačních strategií a salary benchmarkingu
- Talent acquisition a workforce planning
- Souvislostí mezi technologickými trendy a poptávkou po pracovní síle

# KONTEXT ANALÝZY

**Datum analýzy:** {stats.get('analysis_date', 'aktuální týden')}
**Geografický rozsah:** Česká republika
**Datové zdroje:** Jobs.cz, Prace.cz, StartupJobs, WTTJ, Cocuma

# SUROVÁ DATA K ANALÝZE

## 1. Objem a struktura trhu
- **Celkem aktivních nabídek:** {stats.get('total_jobs', 0):,}
- **Rozložení podle rolí:** {json.dumps(stats.get('role_distribution', {}), ensure_ascii=False, indent=2)}
- **Rozložení seniority:** {json.dumps(stats.get('seniority_distribution', {}), ensure_ascii=False, indent=2)}

## 2. Kompenzační data
- **Pokrytí daty o platech:** {stats.get('salary_stats', {}).get('percentage_with_salary', 0)}% nabídek uvádí plat
- **Mediánová mzda (celkový trh):** {stats.get('salary_stats', {}).get('median', 'N/A')} CZK
- **Mediány podle rolí:** {json.dumps(stats.get('salary_stats', {}).get('by_role', {}), ensure_ascii=False, indent=2)}

## 3. Technologická vyspělost zaměstnavatelů
- **Tech stack distribuce:** {json.dumps(stats.get('tech_status', {}), ensure_ascii=False)}
  - "Modern" = React, TypeScript, Kubernetes, cloud-native
  - "Stable" = Java, .NET, established stacks
  - "Dinosaur" = legacy PHP, COBOL, outdated tech

## 4. Smluvní modely
- **Distribuce typů smluv:** {json.dumps(stats.get('contract_distribution', {}), ensure_ascii=False)}
  - HPP = hlavní pracovní poměr (zaměstnanec)
  - IČO = OSVČ/kontraktor
  - Brigáda = částečný úvazek/dohoda

## 5. Geografické rozložení
- **Top lokality:** {json.dumps(stats.get('top_cities', {}), ensure_ascii=False)}

## 6. Datové zdroje
- **Distribuce podle portálu:** {json.dumps(stats.get('source_distribution', {}), ensure_ascii=False)}

# ANALYTICKÝ FRAMEWORK

Proveď následující analytické kroky:

## Krok 1: Kvantitativní analýza
- Identifikuj statisticky významné vzorce v datech
- Porovnej proporce (např. % junior vs senior pozic, % remote, % s uvedeným platem)
- Vypočítej implikované metriky (např. průměrný počet nabídek na roli)

## Krok 2: Kvalitativní interpretace
- Co data vypovídají o zdraví trhu práce?
- Jaké jsou implikace pro náborové strategie?
- Jaké jsou warning signs nebo příležitosti?

## Krok 3: Komparativní kontext
- Jak se data srovnávají s typickým českým trhem?
- Jsou některé metriky neobvyklé nebo alarmující?

## Krok 4: Praktická doporučení
- Konkrétní akce pro HR manažery a recruitery
- Strategie pro zaměstnavatele vs uchazeče

# POŽADOVANÝ VÝSTUP

Vytvoř JSON objekt s touto strukturou:

{{
    "executive_summary": "Komplexní shrnutí stavu trhu (3-4 věty). Zahrň klíčová čísla a jejich interpretaci. Toto je hlavní zpráva pro vedení.",
    
    "market_health_score": {{
        "score": 7,  // 1-10 škála (10 = extrémně zdravý trh)
        "reasoning": "Krátké zdůvodnění skóre"
    }},
    
    "key_insights": [
        {{
            "emoji": "📊",
            "title": "Krátký titulek (max 5 slov)",
            "insight": "Detailní poznatek s konkrétními čísly (1-2 věty)",
            "implication": "Co to znamená pro HR/zaměstnavatele",
            "confidence": "high/medium/low"
        }},
        {{
            "emoji": "💰",
            "title": "Insight o kompenzacích",
            "insight": "Analýza platových dat",
            "implication": "Doporučení pro salary banding",
            "confidence": "high/medium/low"
        }},
        {{
            "emoji": "🎯",
            "title": "Talent supply/demand",
            "insight": "Analýza nabídky vs poptávky",
            "implication": "Implikace pro recruitment strategy",
            "confidence": "high/medium/low"
        }},
        {{
            "emoji": "🔮",
            "title": "Emerging trend",
            "insight": "Pozorovaný nebo předpokládaný trend",
            "implication": "Jak se připravit",
            "confidence": "high/medium/low"
        }},
        {{
            "emoji": "⚠️",
            "title": "Risk nebo varování",
            "insight": "Potenciální problém nebo anomálie v datech",
            "implication": "Mitigační strategie",
            "confidence": "high/medium/low"
        }}
    ],
    
    "strategic_recommendations": {{
        "for_employers": [
            "Konkrétní akční doporučení #1",
            "Konkrétní akční doporučení #2"
        ],
        "for_candidates": [
            "Doporučení pro uchazeče #1",
            "Doporučení pro uchazeče #2"
        ]
    }},
    
    "data_quality_notes": "Poznámka k limitacím dat nebo interpretaci (např. 'Pouze X% nabídek uvádí plat, což může zkreslovat mediány.')"
}}

# PRAVIDLA PRO ODPOVĚĎ

1. **Jazyk:** Piš výhradně v češtině (včetně technických termínů kde to dává smysl)
2. **Přesnost:** Používej POUZE čísla z poskytnutých dat, nevymýšlej
3. **Konkrétnost:** Každý insight musí obsahovat alespoň jedno konkrétní číslo
4. **Akčnost:** Doporučení musí být konkrétní a implementovatelná
5. **Realismus:** Přiznej limitace dat (např. nízké pokrytí platů)
6. **Formát:** Odpověz POUZE validním JSON objektem, žádný další text před nebo za ním

# ZAČNI ANALÝZU"""

        response = model.generate_content(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        # Clean up potential markdown code blocks
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        insights = json.loads(response_text)
        
        # Validate structure
        if 'summary' not in insights or 'key_insights' not in insights:
            raise ValueError("Missing required fields in LLM response")
        
        logger.info("Successfully generated LLM insights")
        return insights
        
    except ImportError:
        logger.warning("google-generativeai not installed. Skipping LLM analysis.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        return {}


def get_llm_insights(df) -> Dict:
    """
    Main entry point for LLM market analysis.
    
    Checks for API key, generates insights, handles failures gracefully.
    
    Returns:
        Dict with insights or empty dict if unavailable
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key:
        logger.info("GEMINI_API_KEY not set. Skipping LLM market analysis.")
        return {
            'summary': '',
            'key_insights': [],
            'trend_alert': None,
            'enabled': False
        }
    
    logger.info("Generating LLM market insights...")
    
    # Get stats
    stats = get_market_stats(df)
    if not stats:
        logger.warning("No market stats available for LLM analysis.")
        return {'summary': '', 'key_insights': [], 'trend_alert': None, 'enabled': False}
    
    # Generate insights
    insights = generate_weekly_insights(stats, api_key)
    
    if insights:
        insights['enabled'] = True
        return insights
    else:
        return {'summary': '', 'key_insights': [], 'trend_alert': None, 'enabled': False}
