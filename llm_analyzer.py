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
        model = genai.GenerativeModel('gemini-3-flash')  # Gemini 3 Flash: fast + high quality
        
        prompt = f"""Jsi HR analytik pro český trh práce. Analyzuj následující data a vytvoř stručný týdenní přehled.

AKTUÁLNÍ DATA:
- Celkem nabídek: {stats.get('total_jobs', 0)}
- Rozložení rolí: {json.dumps(stats.get('role_distribution', {}), ensure_ascii=False)}
- Rozložení seniority: {json.dumps(stats.get('seniority_distribution', {}), ensure_ascii=False)}
- Statistiky platů: {json.dumps(stats.get('salary_stats', {}), ensure_ascii=False)}
- Zdroje dat: {json.dumps(stats.get('source_distribution', {}), ensure_ascii=False)}
- Technologický status: {json.dumps(stats.get('tech_status', {}), ensure_ascii=False)}
- Typ smlouvy: {json.dumps(stats.get('contract_distribution', {}), ensure_ascii=False)}
- Top města: {json.dumps(stats.get('top_cities', {}), ensure_ascii=False)}

ÚKOL:
Vytvoř JSON objekt s následující strukturou:
{{
    "summary": "Krátký odstavec (2-3 věty) shrnující stav trhu práce tento týden.",
    "key_insights": [
        "📊 První klíčový insight (max 15 slov)",
        "💰 Druhý klíčový insight o platech (max 15 slov)",
        "🔥 Třetí insight o trendech (max 15 slov)",
        "⚠️ Čtvrtý insight - upozornění nebo zajímavost (max 15 slov)"
    ],
    "trend_alert": "Jeden výrazný trend nebo varování, pokud existuje. Jinak null."
}}

PRAVIDLA:
- Piš v češtině
- Buď konkrétní - používej čísla z dat
- Každý insight začni relevantním emoji
- Zaměř se na poznatky užitečné pro HR a zaměstnavatele
- Odpověz POUZE validním JSON objektem, žádný další text"""

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
