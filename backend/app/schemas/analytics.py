"""
Analytics schemas for API responses
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime


class OrganizationOverview(BaseModel):
    total_customers: int
    total_branches: int
    total_loan_officers: int
    total_groups: int


class FinancialSummary(BaseModel):
    total_loans_disbursed: int
    total_amount_disbursed: float
    total_payments: int
    total_collected: float
    outstanding_balance: float
    arrears_amount: float
    collection_rate: float
    arrears_rate: float
    growth_rate: float


class LoanBreakdown(BaseModel):
    active: int
    completed: int
    arrears: int
    total: int


class TopPerformer(BaseModel):
    id: int
    name: str
    score: float
    rank: int


class TopPerformers(BaseModel):
    branches: List[TopPerformer]
    loan_officers: List[TopPerformer]


class Alerts(BaseModel):
    high_risk_loans: int
    high_risk_amount: float
    low_stock_items: int
    critical_stock_items: int
    pending_approvals: int


class ProfitInsights(BaseModel):
    total_inventory_value: float
    potential_sales_value: float
    potential_profit: float
    profit_margin: float
    total_products: int


class DailyTrend(BaseModel):
    date: str
    loans_count: int
    loans_amount: float
    payments_count: int
    payments_amount: float


class Trends(BaseModel):
    daily_data: List[DailyTrend]
    period_days: int
    growth_rate: float


class QuickActions(BaseModel):
    loans_due_today: int
    applications_pending: int
    customers_online: int


class DashboardStatsResponse(BaseModel):
    organization_overview: OrganizationOverview
    financial_summary: FinancialSummary
    loan_breakdown: LoanBreakdown
    top_performers: TopPerformers
    alerts: Alerts
    profit_insights: ProfitInsights
    trends: Trends
    quick_actions: QuickActions
    generated_at: str
    scope: str
    user_role: str


class BranchInfo(BaseModel):
    branch_id: int
    branch_name: str
    branch_code: str
    manager_name: str


class BranchKPIs(BaseModel):
    total_customers: int
    total_savings: float
    total_loans: float
    collection_rate: float
    arrears_rate: float
    growth_rate: float


class PerformanceInsights(BaseModel):
    loan_officers: List[Dict[str, Any]]
    groups: List[Dict[str, Any]]
    branch_rank: int


class InventoryStatus(BaseModel):
    total_products: int
    low_stock_alerts: int
    alerts: List[Dict[str, Any]]


class RecentActivity(BaseModel):
    type: str
    description: str
    amount: float
    timestamp: str
    user: str


class BranchAnalyticsResponse(BaseModel):
    dashboard_type: str
    branch_info: BranchInfo
    kpis: BranchKPIs
    performance_insights: PerformanceInsights
    inventory_status: InventoryStatus
    recent_activities: List[RecentActivity]
    period: Dict[str, str]
    generated_at: str


class CustomerInfo(BaseModel):
    name: str
    account_number: str
    registration_status: str
    member_since: str


class AccountSummary(BaseModel):
    savings_balance: float
    drawdown_balance: float
    loan_limit: float
    available_capacity: float
    registration_fee_paid: bool


class LoanOverview(BaseModel):
    total_loans: int
    active_loans: int
    completed_loans: int
    total_borrowed: float
    total_outstanding: float
    next_payment: Optional[Dict[str, Any]]


class AvailableProduct(BaseModel):
    product_id: int
    product_name: str
    category: str
    price: float
    description: str


class PaymentScheduleItem(BaseModel):
    loan_number: str
    due_date: str
    amount: float
    days_remaining: int
    can_auto_pay: bool


class RecentTransaction(BaseModel):
    transaction_number: str
    type: str
    account: str
    amount: float
    balance_after: float
    date: str
    description: str


class CustomerDashboardResponse(BaseModel):
    dashboard_type: str
    customer_info: CustomerInfo
    account_summary: AccountSummary
    loan_overview: LoanOverview
    available_products: List[AvailableProduct]
    payment_schedule: List[PaymentScheduleItem]
    recent_transactions: List[RecentTransaction]
    generated_at: str


class RiskFactor(BaseModel):
    factor: str
    score: float
    weight: float
    description: str


class RiskRecommendation(BaseModel):
    priority: str
    action: str
    expected_impact: str


class CustomerRiskResponse(BaseModel):
    customer_id: int
    risk_score: float
    risk_level: str
    risk_factors: List[RiskFactor]
    recommendations: List[RiskRecommendation]
    confidence_score: float
    last_updated: str


class LeaderboardEntry(BaseModel):
    id: int
    name: str
    score: float
    rank: int
    metrics: Dict[str, Any]


class PerformanceLeaderboardResponse(BaseModel):
    leaderboard_type: str
    title: str
    rankings: List[LeaderboardEntry]
    total_entries: int
    generated_at: str


class RiskCategory(BaseModel):
    category: str
    count: int
    amount: float
    percentage: float


class ForecastData(BaseModel):
    date: str
    predicted_arrears: float
    confidence_interval: Dict[str, float]
    risk_factors: List[str]


class ForecastResponse(BaseModel):
    forecast_period_days: int
    risk_categories: Dict[str, RiskCategory]
    forecast_data: List[ForecastData]
    overall_risk_score: float
    recommendations: List[str]
    generated_at: str
    model_accuracy: float
