"""
Chart Builder Module

Provides reusable chart creation functions for the HR Intelligence report.
Extracted from generate_report.py for maintainability.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Optional, Any


# Default layout settings for consistent styling
DEFAULT_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'margin': dict(l=0, r=0, t=30, b=0),
    'height': 360,
    'font': dict(family="Inter, sans-serif", size=12, color="#333")
}


def format_number_cz(number: Optional[float]) -> str:
    """Format number with Czech thousand separator (space)."""
    if number is None or pd.isna(number):
        return "N/A"
    try:
        return f"{int(number):,}".replace(",", " ")
    except (ValueError, TypeError):
        return str(number)


def format_currency_cz(amount: Optional[float]) -> str:
    """Format currency in Czech format (e.g., '50 000 Kč')."""
    if amount is None or pd.isna(amount):
        return "N/A"
    return f"{format_number_cz(amount)} Kč"


def create_donut_chart(
    labels: List[str],
    values: List[int],
    title: str = "",
    colors: Optional[List[str]] = None
) -> go.Figure:
    """Create a donut/pie chart with consistent styling."""
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        textposition='inside',
        textinfo='percent+label',
        marker=dict(colors=colors) if colors else None
    )])
    layout = DEFAULT_LAYOUT.copy()
    layout['title'] = title
    fig.update_layout(**layout, showlegend=True)
    return fig


def create_horizontal_bar_chart(
    categories: List[str],
    values: List[float],
    title: str = "",
    color: str = "#36A2EB",
    value_suffix: str = ""
) -> go.Figure:
    """Create a horizontal bar chart with consistent styling."""
    fig = go.Figure(data=[go.Bar(
        y=categories,
        x=values,
        orientation='h',
        marker_color=color,
        text=[f"{format_number_cz(v)}{value_suffix}" for v in values],
        textposition='outside'
    )])
    layout = DEFAULT_LAYOUT.copy()
    layout['title'] = title
    layout['yaxis'] = dict(categoryorder='total ascending')
    fig.update_layout(**layout)
    fig.update_yaxes(title="")
    fig.update_xaxes(title="")
    return fig


def create_salary_percentile_chart(
    role_types: List[str],
    p25_values: List[float],
    median_values: List[float],
    p75_values: List[float]
) -> go.Figure:
    """Create a grouped bar chart showing salary percentiles by role."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=role_types,
        x=p25_values,
        name='25th Percentile (Entry)',
        orientation='h',
        marker=dict(color='#FFCE56')
    ))
    fig.add_trace(go.Bar(
        y=role_types,
        x=median_values,
        name='Median Advertised Salary',
        orientation='h',
        marker=dict(color='#36A2EB')
    ))
    fig.add_trace(go.Bar(
        y=role_types,
        x=p75_values,
        name='75th Percentile (Aspirational)',
        orientation='h',
        marker=dict(color='#FF6384')
    ))
    
    layout = DEFAULT_LAYOUT.copy()
    layout['barmode'] = 'group'
    layout['height'] = 500
    fig.update_layout(**layout)
    fig.update_yaxes(title="")
    fig.update_xaxes(title="Monthly CZK")
    
    return fig


def create_seniority_salary_chart(
    seniority_levels: List[str],
    salaries: List[float]
) -> go.Figure:
    """Create a bar chart showing salary by seniority level."""
    # Order by seniority progression
    order = ['Junior', 'Mid', 'Senior', 'Lead', 'Executive']
    sorted_data = sorted(
        zip(seniority_levels, salaries),
        key=lambda x: order.index(x[0]) if x[0] in order else 99
    )
    levels, sals = zip(*sorted_data) if sorted_data else ([], [])
    
    fig = go.Figure(data=[go.Bar(
        x=list(levels),
        y=list(sals),
        marker_color='#4BC0C0',
        text=[format_currency_cz(s) for s in sals],
        textposition='outside'
    )])
    
    layout = DEFAULT_LAYOUT.copy()
    layout['height'] = 320
    fig.update_layout(**layout)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Median Salary (CZK)")
    
    return fig


def create_tech_stack_chart(
    tech_levels: List[str],
    counts: List[int],
    colors: Optional[Dict[str, str]] = None
) -> go.Figure:
    """Create a pie chart showing tech stack distribution (Modern/Stable/Legacy)."""
    default_colors = {
        'Modern': '#4BC0C0',
        'Stable': '#36A2EB',
        'Dinosaur': '#FF6384'
    }
    color_list = [
        (colors or default_colors).get(level, '#999')
        for level in tech_levels
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=tech_levels,
        values=counts,
        marker_colors=color_list,
        textinfo='percent+label'
    )])
    
    layout = DEFAULT_LAYOUT.copy()
    fig.update_layout(**layout)
    
    return fig
