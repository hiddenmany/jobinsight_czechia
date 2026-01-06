"""
Report Package

Provides modular components for generating the HR Intelligence report.
"""

from report.chart_builder import (
    create_donut_chart,
    create_horizontal_bar_chart,
    create_salary_percentile_chart,
    create_seniority_salary_chart,
    create_tech_stack_chart,
    format_number_cz,
    format_currency_cz,
    DEFAULT_LAYOUT
)

__all__ = [
    'create_donut_chart',
    'create_horizontal_bar_chart',
    'create_salary_percentile_chart',
    'create_seniority_salary_chart',
    'create_tech_stack_chart',
    'format_number_cz',
    'format_currency_cz',
    'DEFAULT_LAYOUT'
]
