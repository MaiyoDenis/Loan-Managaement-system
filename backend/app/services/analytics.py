"""
Advanced Analytics Engine with Predictive Capabilities
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database import SessionLocal
from app.models.loan import Loan, Payment, SavingsAccount, LoanProduct, BranchInventory, LoanApplication
from app.models.user import User
from app.models.branch import Branch, Group
from app.core.permissions import UserRole


class AdvancedAnalyticsEngine:
    """Advanced analytics engine with predictive capabilities"""
    
    def __init__(self):
        self.seasonal_factors = self._initialize_seasonal_factors()
    
    def _initialize_seasonal_factors(self) -> Dict[int, float]:
        """Initialize seasonal adjustment factors for Kenya"""
        return {
            1: 0.9,   # January - Post-holiday recovery
            2: 0.95,  # February - Normalized
            3: 1.0,   # March - Normal
            4: 1.1,   # April - School fees season
            5: 0.9,   # May - Post-school fees
            6: 1.0,   # June - Normal
            7: 1.0,   # July - Normal
            8: 1.1,   # August - Back to school
            9: 0.95,  # September - Post-school fees
            10: 1.0,  # October - Normal
            11: 1.05, # November - Pre-holiday preparation
            12: 0.85  # December - Holiday season (lower collections)
        }
    
    def generate_comprehensive_analytics(self, branch_id: Optional[int] = None, 
                                       user_role: UserRole = UserRole.ADMIN) -> Dict[str, Any]:
        """Generate comprehensive analytics dashboard"""
        db = SessionLocal()
        try:
            analytics = {
                "overview": self._get_financial_overview(db, branch_id, user_role),
                "performance_metrics": self._calculate_performance_metrics(db, branch_id),
                "risk_analysis": self._analyze_risk_distribution(db, branch_id),
                "trend_analysis": self._analyze_trends(db, branch_id),
                "forecasting": self._generate_forecasts(db, branch_id),
                "alerts": self._generate_smart_alerts(db, branch_id),
                "recommendations": self._generate_recommendations(db, branch_id)
            }
            
            return analytics
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()
    
    def _get_financial_overview(self, db: Session, branch_id: Optional[int], 
                               user_role: UserRole) -> Dict[str, Any]:
        """Get financial overview with KPIs"""
        
        # Build base queries
        loans_query = db.query(Loan)
        payments_query = db.query(Payment)
        savings_query = db.query(SavingsAccount).join(User)
        
        # Apply branch filtering
        if branch_id:
            branch_users = db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            user_ids = [u.id for u in branch_users]
            
            loans_query = loans_query.filter(Loan.borrower_id.in_(user_ids))
            payments_query = payments_query.join(Loan).filter(Loan.borrower_id.in_(user_ids))
            savings_query = savings_query.filter(User.id.in_(user_ids))
        
        # Get data
        all_loans = loans_query.all()
        all_payments = payments_query.filter(Payment.status == 'confirmed').all()
        all_savings = savings_query.all()
        
        # Calculate totals
        total_disbursed = sum(float(loan.total_amount) for loan in all_loans)
        total_collected = sum(float(payment.amount) for payment in all_payments)
        total_outstanding = sum(float(loan.balance) for loan in all_loans if loan.status in ['active', 'arrears'])
        total_savings = sum(float(acc.balance) for acc in all_savings)
        
        # Calculate KPIs
        collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 0
        
        # Portfolio at Risk (PAR) - loans overdue > 30 days
        overdue_loans = [loan for loan in all_loans if loan.is_overdue and (date.today() - loan.due_date).days > 30]
        par_amount = sum(float(loan.balance) for loan in overdue_loans)
        par_ratio = (par_amount / total_outstanding * 100) if total_outstanding > 0 else 0
        
        # Profit calculations (admin only)
        if user_role == UserRole.ADMIN:
            # Calculate interest income
            interest_income = sum(float(loan.interest_amount) for loan in all_loans)
            charge_fee_income = sum(float(loan.charge_fee_amount) for loan in all_loans)
            
            # Calculate product profit margins
            product_profits = self._calculate_product_profits(db, branch_id)
            
            gross_profit = interest_income + charge_fee_income + product_profits["total_profit"]
        else:
            interest_income = None
            charge_fee_income = None
            gross_profit = None
            product_profits = None
        
        return {
            "total_customers": len(set(loan.borrower_id for loan in all_loans)),
            "total_loans": len(all_loans),
            "active_loans": len([l for l in all_loans if l.status == 'active']),
            "completed_loans": len([l for l in all_loans if l.status == 'completed']),
            "arrears_loans": len([l for l in all_loans if l.status == 'arrears']),
            "total_disbursed": total_disbursed,
            "total_collected": total_collected,
            "total_outstanding": total_outstanding,
            "total_savings": total_savings,
            "collection_rate": round(collection_rate, 2),
            "par_ratio": round(par_ratio, 2),
            "par_amount": par_amount,
            "interest_income": interest_income,
            "charge_fee_income": charge_fee_income,
            "gross_profit": gross_profit,
            "product_profits": product_profits
        }
    
    def _calculate_performance_metrics(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Calculate detailed performance metrics"""
        
        # Time periods for comparison
        today = date.today()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        this_year_start = today.replace(month=1, day=1)
        
        # Build queries with branch filtering
        base_query = db.query(Payment).join(Loan)
        
        if branch_id:
            branch_users = db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            user_ids = [u.id for u in branch_users]
            base_query = base_query.filter(Loan.borrower_id.in_(user_ids))
        
        # This month performance
        this_month_payments = base_query.filter(
            Payment.payment_date >= this_month_start,
            Payment.status == 'confirmed'
        ).all()
        
        # Last month performance
        last_month_payments = base_query.filter(
            and_(
                Payment.payment_date >= last_month_start,
                Payment.payment_date < this_month_start
            ),
            Payment.status == 'confirmed'
        ).all()
        
        # Year to date performance
        ytd_payments = base_query.filter(
            Payment.payment_date >= this_year_start,
            Payment.status == 'confirmed'
        ).all()
        
        # Calculate metrics
        this_month_total = sum(float(p.amount) for p in this_month_payments)
        last_month_total = sum(float(p.amount) for p in last_month_payments)
        ytd_total = sum(float(p.amount) for p in ytd_payments)
        
        # Growth calculations
        month_over_month_growth = ((this_month_total - last_month_total) / last_month_total * 100) if last_month_total > 0 else 0
        
        # Payment method breakdown
        payment_methods = {}
        for payment in this_month_payments:
            method = payment.payment_method
            if method not in payment_methods:
                payment_methods[method] = {"count": 0, "amount": 0.0}
            
            payment_methods[method]["count"] += 1
            payment_methods[method]["amount"] += float(payment.amount)
        
        return {
            "this_month": {
                "total_amount": this_month_total,
                "total_count": len(this_month_payments),
                "avg_payment": this_month_total / len(this_month_payments) if this_month_payments else 0
            },
            "last_month": {
                "total_amount": last_month_total,
                "total_count": len(last_month_payments),
                "avg_payment": last_month_total / len(last_month_payments) if last_month_payments else 0
            },
            "year_to_date": {
                "total_amount": ytd_total,
                "total_count": len(ytd_payments),
                "avg_payment": ytd_total / len(ytd_payments) if ytd_payments else 0
            },
            "growth_metrics": {
                "month_over_month": round(month_over_month_growth, 2),
                "trend": "up" if month_over_month_growth > 0 else "down" if month_over_month_growth < 0 else "stable"
            },
            "payment_methods": payment_methods
        }
    
    def _analyze_risk_distribution(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Analyze risk distribution across portfolio"""
        
        # Get loans with risk categorization
        loans_query = db.query(Loan)
        
        if branch_id:
            branch_users = db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            user_ids = [u.id for u in branch_users]
            loans_query = loans_query.filter(Loan.borrower_id.in_(user_ids))
        
        active_loans = loans_query.filter(
            Loan.status.in_(['active', 'arrears']),
            Loan.balance > 0
        ).all()
        
        # Categorize loans by risk
        current_loans = []
        overdue_loans = []
        arrears_loans = []
        
        for loan in active_loans:
            if loan.status == 'arrears':
                arrears_loans.append(loan)
            elif loan.due_date < date.today():
                overdue_loans.append(loan)
            else:
                current_loans.append(loan)
        
        # Calculate amounts
        current_amount = sum(float(loan.balance) for loan in current_loans)
        overdue_amount = sum(float(loan.balance) for loan in overdue_loans)
        arrears_amount = sum(float(loan.balance) for loan in arrears_loans)
        total_at_risk = current_amount + overdue_amount + arrears_amount
        
        # Risk distribution by days overdue
        risk_buckets = {
            "0-30 days": [],
            "31-60 days": [],
            "61-90 days": [], 
            "90+ days": []
        }
        
        for loan in overdue_loans + arrears_loans:
            days_overdue = (date.today() - loan.due_date).days
            
            if days_overdue <= 30:
                risk_buckets["0-30 days"].append(loan)
            elif days_overdue <= 60:
                risk_buckets["31-60 days"].append(loan)
            elif days_overdue <= 90:
                risk_buckets["61-90 days"].append(loan)
            else:
                risk_buckets["90+ days"].append(loan)
        
        bucket_analysis = {}
        for bucket, loans in risk_buckets.items():
            bucket_analysis[bucket] = {
                "count": len(loans),
                "amount": sum(float(loan.balance) for loan in loans),
                "percentage": (len(loans) / len(active_loans) * 100) if active_loans else 0
            }
        
        return {
            "total_active_loans": len(active_loans),
            "total_amount_at_risk": total_at_risk,
            "risk_categories": {
                "current": {"count": len(current_loans), "amount": current_amount},
                "overdue": {"count": len(overdue_loans), "amount": overdue_amount},
                "arrears": {"count": len(arrears_loans), "amount": arrears_amount}
            },
            "risk_buckets": bucket_analysis,
            "par_30": bucket_analysis["0-30 days"]["amount"] + bucket_analysis["31-60 days"]["amount"] + bucket_analysis["61-90 days"]["amount"] + bucket_analysis["90+ days"]["amount"],
            "par_90": bucket_analysis["61-90 days"]["amount"] + bucket_analysis["90+ days"]["amount"]
        }
    
    def _analyze_trends(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Analyze financial trends over time"""
        
        # Get last 12 months of data
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        # Build monthly data
        monthly_data = []
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            next_month = (current_date + timedelta(days=32)).replace(day=1)
            
            # Get month data
            month_query = db.query(Payment).join(Loan)
            
            if branch_id:
                branch_users = db.query(User).filter(
                    User.branch_id == branch_id,
                    User.role == UserRole.CUSTOMER
                ).all()
                user_ids = [u.id for u in branch_users]
                month_query = month_query.filter(Loan.borrower_id.in_(user_ids))
            
            month_payments = month_query.filter(
                and_(
                    Payment.payment_date >= current_date,
                    Payment.payment_date < next_month
                ),
                Payment.status == 'confirmed'
            ).all()
            
            # Calculate month metrics
            month_total = sum(float(p.amount) for p in month_payments)
            month_count = len(month_payments)
            
            # Get loans disbursed in this month
            month_loans = db.query(Loan).filter(
                and_(
                    Loan.start_date >= current_date,
                    Loan.start_date < next_month
                )
            )
            
            if branch_id:
                month_loans = month_loans.filter(Loan.borrower_id.in_(user_ids))
            
            month_loans_list = month_loans.all()
            month_disbursed = sum(float(loan.total_amount) for loan in month_loans_list)
            
            monthly_data.append({
                "month": current_date.strftime('%Y-%m'),
                "month_name": current_date.strftime('%B %Y'),
                "payments_total": month_total,
                "payments_count": month_count,
                "loans_disbursed": month_disbursed,
                "loans_count": len(month_loans_list),
                "collection_rate": (month_total / month_disbursed * 100) if month_disbursed > 0 else 0
            })
            
            current_date = next_month
        
        # Calculate trends
        recent_months = monthly_data[-3:]  # Last 3 months
        older_months = monthly_data[-6:-3]  # 3 months before that
        
        recent_avg = np.mean([m["payments_total"] for m in recent_months]) if recent_months else 0
        older_avg = np.mean([m["payments_total"] for m in older_months]) if older_months else 0
        
        trend_direction = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
        trend_percentage = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        return {
            "monthly_data": monthly_data,
            "trend_analysis": {
                "direction": trend_direction,
                "percentage_change": round(trend_percentage, 2),
                "recent_average": round(recent_avg, 2),
                "older_average": round(older_avg, 2)
            },
            "seasonality": self._analyze_seasonality(monthly_data)
        }
    
    def _analyze_seasonality(self, monthly_data: List[Dict]) -> Dict[str, Any]:
        """Analyze seasonal patterns in payments"""
        if len(monthly_data) < 12:
            return {"insufficient_data": True}
        
        # Group by month of year
        seasonal_patterns = {}
        for data in monthly_data:
            month_num = int(data["month"].split('-')[1])
            
            if month_num not in seasonal_patterns:
                seasonal_patterns[month_num] = []
            
            seasonal_patterns[month_num].append(data["payments_total"])
        
        # Calculate averages
        seasonal_averages = {}
        for month_num, amounts in seasonal_patterns.items():
            seasonal_averages[month_num] = {
                "average": np.mean(amounts),
                "month_name": date(2024, month_num, 1).strftime('%B'),
                "data_points": len(amounts)
            }
        
        # Find peak and low seasons
        avg_amounts = [data["average"] for data in seasonal_averages.values()]
        overall_avg = np.mean(avg_amounts)
        
        peak_months = [month for month, data in seasonal_averages.items() if data["average"] > overall_avg * 1.1]
        low_months = [month for month, data in seasonal_averages.items() if data["average"] < overall_avg * 0.9]
        
        return {
            "seasonal_averages": seasonal_averages,
            "overall_average": round(overall_avg, 2),
            "peak_months": peak_months,
            "low_months": low_months,
            "seasonal_variance": round(np.std(avg_amounts), 2)
        }
    
    def _generate_forecasts(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Generate predictive forecasts"""
        
        # Get historical data for forecasting
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        historical_query = db.query(Payment).join(Loan)
        
        if branch_id:
            branch_users = db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            user_ids = [u.id for u in branch_users]
            historical_query = historical_query.filter(Loan.borrower_id.in_(user_ids))
        
        historical_payments = historical_query.filter(
            Payment.payment_date >= start_date,
            Payment.status == 'confirmed'
        ).all()
        
        # Group by week for trend analysis
        weekly_data = {}
        for payment in historical_payments:
            # Get week start (Monday)
            week_start = payment.payment_date - timedelta(days=payment.payment_date.weekday())
            week_key = week_start.strftime('%Y-%W')
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {"amount": 0.0, "count": 0}
            
            weekly_data[week_key]["amount"] += float(payment.amount)
            weekly_data[week_key]["count"] += 1
        
        # Calculate trend using simple linear regression
        weeks = sorted(weekly_data.keys())
        amounts = [weekly_data[week]["amount"] for week in weeks]
        
        if len(amounts) >= 4:
            # Simple trend calculation
            x = np.arange(len(amounts))
            z = np.polyfit(x, amounts, 1)
            trend_slope = z[0]
            
            # Forecast next 4 weeks
            forecast_weeks = []
            for i in range(1, 5):
                future_week = end_date + timedelta(weeks=i)
                future_week_start = future_week - timedelta(days=future_week.weekday())
                
                # Apply trend and seasonal factors
                base_forecast = amounts[-1] + (trend_slope * i)
                seasonal_factor = self.seasonal_factors.get(future_week.month, 1.0)
                adjusted_forecast = base_forecast * seasonal_factor
                
                forecast_weeks.append({
                    "week_start": future_week_start.strftime('%Y-%m-%d'),
                    "forecasted_amount": max(0, round(adjusted_forecast, 2)),
                    "confidence": "Medium" if len(amounts) >= 8 else "Low"
                })
            
            # Forecast potential arrears
            arrears_forecast = self._forecast_arrears(db, branch_id)
            
            return {
                "weekly_forecast": forecast_weeks,
                "trend_slope": round(trend_slope, 2),
                "trend_direction": "increasing" if trend_slope > 0 else "decreasing" if trend_slope < 0 else "stable",
                "arrears_forecast": arrears_forecast,
                "data_quality": "Good" if len(amounts) >= 12 else "Limited"
            }
        else:
            return {
                "error": "Insufficient historical data for forecasting",
                "min_required_weeks": 4,
                "available_weeks": len(amounts)
            }
    
    def _forecast_arrears(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Forecast potential arrears in next 2 weeks"""
        
        # Get loans due in next 14 days
        end_date = date.today() + timedelta(days=14)
        
        upcoming_due_query = db.query(Loan).filter(
            Loan.next_payment_date <= end_date,
            Loan.status == 'active',
            Loan.balance > 0
        )
        
        if branch_id:
            branch_users = db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            user_ids = [u.id for u in branch_users]
            upcoming_due_query = upcoming_due_query.filter(Loan.borrower_id.in_(user_ids))
        
        upcoming_loans = upcoming_due_query.all()
        
        # Analyze each loan's arrears probability
        arrears_forecast = []
        total_at_risk_amount = 0
        high_risk_count = 0
        
        for loan in upcoming_loans:
            # Get borrower's risk factors
            borrower = loan.borrower
            
            # Check drawdown balance vs required payment
            drawdown_balance = float(borrower.drawdown_account.balance) if borrower.drawdown_account else 0
            required_payment = float(loan.next_payment_amount or loan.balance)
            
            # Calculate arrears probability
            if drawdown_balance >= required_payment:
                arrears_probability = 0.1  # Low risk
                risk_level = "Low"
            elif drawdown_balance >= required_payment * 0.7:
                arrears_probability = 0.3  # Medium risk
                risk_level = "Medium"
            elif drawdown_balance >= required_payment * 0.3:
                arrears_probability = 0.6  # High risk
                risk_level = "High"
            else:
                arrears_probability = 0.9  # Very high risk
                risk_level = "Very High"
            
            # Adjust based on payment history
            from app.services.risk_scoring import risk_engine
            payment_history_score = risk_engine._calculate_payment_history_score(db, borrower)
            history_adjustment = (payment_history_score - 50) / 500  # -0.1 to +0.1
            
            final_probability = max(0, min(1, arrears_probability + history_adjustment))
            
            if final_probability > 0.5:
                high_risk_count += 1
                total_at_risk_amount += required_payment
            
            arrears_forecast.append({
                "loan_id": loan.id,
                "loan_number": loan.loan_number,
                "borrower_name": f"{borrower.first_name} {borrower.last_name}",
                "due_date": loan.next_payment_date.strftime('%Y-%m-%d'),
                "required_payment": required_payment,
                "available_balance": drawdown_balance,
                "shortfall": max(0, required_payment - drawdown_balance),
                "arrears_probability": round(final_probability, 2),
                "risk_level": risk_level,
                "days_until_due": (loan.next_payment_date - date.today()).days
            })
        
        # Sort by arrears probability (highest risk first)
        arrears_forecast.sort(key=lambda x: x["arrears_probability"], reverse=True)
        
        return {
            "total_loans_due": len(upcoming_loans),
            "high_risk_loans": high_risk_count,
            "total_at_risk_amount": total_at_risk_amount,
            "forecast_details": arrears_forecast[:20],  # Top 20 risky loans
            "summary": {
                "low_risk": len([f for f in arrears_forecast if f["arrears_probability"] <= 0.3]),
                "medium_risk": len([f for f in arrears_forecast if 0.3 < f["arrears_probability"] <= 0.6]),
                "high_risk": len([f for f in arrears_forecast if f["arrears_probability"] > 0.6])
            }
        }
    
    def _generate_smart_alerts(self, db: Session, branch_id: Optional[int]) -> List[Dict[str, Any]]:
        """Generate intelligent alerts based on data analysis"""
        alerts = []
        
        # Critical inventory alerts
        inventory_alerts = self._check_critical_inventory(db, branch_id)
        alerts.extend(inventory_alerts)
        
        # Payment performance alerts
        performance_alerts = self._check_performance_issues(db, branch_id)
        alerts.extend(performance_alerts)
        
        # Risk alerts
        risk_alerts = self._check_risk_indicators(db, branch_id)
        alerts.extend(risk_alerts)
        
        # Opportunity alerts
        opportunity_alerts = self._identify_opportunities(db, branch_id)
        alerts.extend(opportunity_alerts)
        
        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return alerts
    
    def _check_critical_inventory(self, db: Session, branch_id: Optional[int]) -> List[Dict[str, Any]]:
        """Check for critical inventory issues"""
        alerts = []
        
        inventory_query = db.query(BranchInventory).join(LoanProduct)
        
        if branch_id:
            inventory_query = inventory_query.filter(BranchInventory.branch_id == branch_id)
        
        inventory_items = inventory_query.all()
        
        for item in inventory_items:
            if item.current_quantity == 0:
                alerts.append({
                    "type": "inventory",
                    "priority": "critical",
                    "title": "Out of Stock",
                    "message": f"{item.loan_product.name} is out of stock in {item.branch.name}",
                    "action_required": "Immediate restocking required",
                    "branch_id": item.branch_id,
                    "product_id": item.loan_product_id
                })
            elif item.current_quantity <= item.critical_point:
                alerts.append({
                    "type": "inventory",
                    "priority": "high",
                    "title": "Critical Stock Level",
                    "message": f"{item.loan_product.name} has only {item.current_quantity} units left",
                    "action_required": "Urgent restocking required",
                    "branch_id": item.branch_id,
                    "product_id": item.loan_product_id
                })
            elif item.current_quantity <= item.reorder_point:
                alerts.append({
                    "type": "inventory",
                    "priority": "medium",
                    "title": "Low Stock Level",
                    "message": f"{item.loan_product.name} needs restocking ({item.current_quantity} units)",
                    "action_required": "Schedule restocking",
                    "branch_id": item.branch_id,
                    "product_id": item.loan_product_id
                })
        
        return alerts
    
    def _check_performance_issues(self, db: Session, branch_id: Optional[int]) -> List[Dict[str, Any]]:
        """Check for performance issues"""
        alerts = []
        
        # Check collection rate issues
        overview = self._get_financial_overview(db, branch_id, UserRole.ADMIN)
        
        if overview["collection_rate"] < 85:
            alerts.append({
                "type": "performance",
                "priority": "high",
                "title": "Low Collection Rate",
                "message": f"Collection rate is {overview['collection_rate']:.1f}% (target: 85%)",
                "action_required": "Review collection strategies",
                "metric_value": overview["collection_rate"],
                "target_value": 85
            })
        
        if overview["par_ratio"] > 5:
            alerts.append({
                "type": "performance", 
                "priority": "high",
                "title": "High Portfolio at Risk",
                "message": f"PAR ratio is {overview['par_ratio']:.1f}% (target: <5%)",
                "action_required": "Intensify collection efforts",
                "metric_value": overview["par_ratio"],
                "target_value": 5
            })
        
        # Check for declining trends
        trends = self._analyze_trends(db, branch_id)
        if trends.get("trend_analysis", {}).get("direction") == "down":
            change = trends["trend_analysis"]["percentage_change"]
            if abs(change) > 15:
                alerts.append({
                    "type": "performance",
                    "priority": "medium",
                    "title": "Declining Payment Trend",
                    "message": f"Payments decreased by {abs(change):.1f}% in recent months",
                    "action_required": "Investigate causes and implement corrective measures",
                    "trend_change": change
                })
        
        return alerts
    
    def _check_risk_indicators(self, db: Session, branch_id: Optional[int]) -> List[Dict[str, Any]]:
        """Check for risk indicators"""
        alerts = []
        
        # Check for high-risk loan applications
        from app.models.loan import LoanApplication
        from app.services.risk_scoring import risk_engine
        
        pending_applications = db.query(LoanApplication).filter(
            LoanApplication.status.in_(['submitted', 'pending', 'under_review'])
        )
        
        if branch_id:
            from app.models.branch import Group
            branch_groups = db.query(Group).filter(Group.branch_id == branch_id).all()
            group_ids = [g.id for g in branch_groups]
            pending_applications = pending_applications.filter(
                LoanApplication.group_id.in_(group_ids)
            )
        
        for application in pending_applications.all():
            risk_data = risk_engine.calculate_risk_score(application.applicant_id)
            
            if not risk_data.get("error") and risk_data.get("risk_score", 100) < 40:
                alerts.append({
                    "type": "risk",
                    "priority": "high",
                    "title": "High-Risk Loan Application",
                    "message": f"Application {application.application_number} has risk score of {risk_data['risk_score']}",
                    "action_required": "Detailed review required before approval",
                    "application_id": application.id,
                    "risk_score": risk_data["risk_score"]
                })
        
        return alerts
    
    def _identify_opportunities(self, db: Session, branch_id: Optional[int]) -> List[Dict[str, Any]]:
        """Identify business opportunities"""
        alerts = []
        
        # Check for customers with high savings but no loans
        savings_query = db.query(SavingsAccount).join(User).filter(
            SavingsAccount.balance >= 5000,
            SavingsAccount.registration_fee_paid == True
        )
        
        if branch_id:
            savings_query = savings_query.filter(User.branch_id == branch_id)
        
        high_savings_customers = savings_query.all()
        
        for savings_account in high_savings_customers:
            active_loans = db.query(Loan).filter(
                Loan.borrower_id == savings_account.user_id,
                Loan.status == 'active'
            ).count()
            
            if active_loans == 0:
                alerts.append({
                    "type": "opportunity",
                    "priority": "low",
                    "title": "Potential Loan Customer",
                    "message": f"Customer {savings_account.user.first_name} has KES {savings_account.balance:,.0f} savings but no active loans",
                    "action_required": "Consider loan marketing outreach",
                    "customer_id": savings_account.user_id,
                    "savings_amount": float(savings_account.balance),
                    "loan_limit": float(savings_account.loan_limit)
                })
        
        return alerts
    
    def _calculate_product_profits(self, db: Session, branch_id: Optional[int]) -> Dict[str, Any]:
        """Calculate product profit analysis"""
        
        # Get product sales through loans
        product_query = db.query(LoanProduct)
        inventory_query = db.query(BranchInventory)
        
        if branch_id:
            inventory_query = inventory_query.filter(BranchInventory.branch_id == branch_id)
        
        products = product_query.all()
        total_profit = 0.0
        product_analysis = []
        
        for product in products:
            # Calculate profit per unit
            profit_per_unit = float(product.selling_price - product.buying_price)
            
            # Get total inventory
            if branch_id:
                inventory = inventory_query.filter(
                    BranchInventory.loan_product_id == product.id
                ).first()
                current_stock = inventory.current_quantity if inventory else 0
            else:
                total_stock = db.query(func.sum(BranchInventory.current_quantity)).filter(
                    BranchInventory.loan_product_id == product.id
                ).scalar() or 0
                current_stock = int(total_stock)
            
            # Calculate sales through loans (approximation)
            from app.models.loan import LoanApplicationProduct
            
            sales_query = db.query(LoanApplicationProduct).join(LoanApplication).filter(
                LoanApplicationProduct.loan_product_id == product.id,
                LoanApplication.status == 'disbursed'
            )
            
            if branch_id:
                from app.models.branch import Group
                branch_groups = db.query(Group).filter(Group.branch_id == branch_id).all()
                group_ids = [g.id for g in branch_groups]
                sales_query = sales_query.filter(LoanApplication.group_id.in_(group_ids))
            
            total_sold = db.query(func.sum(LoanApplicationProduct.quantity)).filter(
                sales_query.statement.compile().where
            ).scalar() or 0
            
            product_profit = profit_per_unit * int(total_sold)
            total_profit += product_profit
            
            product_analysis.append({
                "product_id": product.id,
                "product_name": product.name,
                "profit_per_unit": profit_per_unit,
                "units_sold": int(total_sold),
                "total_profit": product_profit,
                "current_stock": current_stock,
                "profit_margin": float(product.profit_margin)
            })
        
        # Sort by total profit (highest first)
        product_analysis.sort(key=lambda x: x["total_profit"], reverse=True)
        
        return {
            "total_profit": total_profit,
            "products": product_analysis,
            "top_performers": product_analysis[:5],
            "low_performers": [p for p in product_analysis if p["total_profit"] < 1000]
        }


# Initialize analytics engine
analytics_engine = AdvancedAnalyticsEngine()