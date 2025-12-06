"""
Advanced Analytics & AI-Powered Risk Scoring Engine
This is the BRAIN of your loan management system - predicts risk, analyzes performance, and provides insights
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
import json
import logging

from app.database import SessionLocal
from app.models.loan import (
    Loan, Payment, Arrear, SavingsAccount, DrawdownAccount, 
    LoanApplication, BranchInventory
)
from app.models.user import User
from app.models.branch import Branch, Group, GroupMembership
from app.core.permissions import UserRole

logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """
    AI-Powered Analytics Engine for Loan Management
    Features: Risk Scoring, Predictive Analytics, Performance Metrics, Forecasting
    """
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    # ==================== RISK SCORING SYSTEM ====================
    
    def calculate_customer_risk_score(self, customer_id: int) -> Dict[str, Any]:
        """
        Calculate comprehensive risk score for a customer using AI algorithms
        Score: 0-100 (0 = Highest Risk, 100 = Lowest Risk)
        """
        try:
            customer = self.db.query(User).filter(User.id == customer_id).first()
            if not customer:
                return {"error": "Customer not found"}
            
            # Initialize risk factors
            risk_factors = {}
            
            # 1. PAYMENT HISTORY ANALYSIS (40% weight)
            payment_score = self._analyze_payment_history(customer_id)
            risk_factors['payment_history'] = payment_score
            
            # 2. SAVINGS BEHAVIOR ANALYSIS (25% weight)
            savings_score = self._analyze_savings_behavior(customer_id)
            risk_factors['savings_behavior'] = savings_score
            
            # 3. LOAN UTILIZATION ANALYSIS (20% weight)
            utilization_score = self._analyze_loan_utilization(customer_id)
            risk_factors['loan_utilization'] = utilization_score
            
            # 4. GROUP PERFORMANCE ANALYSIS (10% weight)
            group_score = self._analyze_group_performance(customer_id)
            risk_factors['group_performance'] = group_score
            
            # 5. ACCOUNT STABILITY ANALYSIS (5% weight)
            stability_score = self._analyze_account_stability(customer_id)
            risk_factors['account_stability'] = stability_score
            
            # Calculate weighted risk score
            weights = {
                'payment_history': 0.40,
                'savings_behavior': 0.25,
                'loan_utilization': 0.20,
                'group_performance': 0.10,
                'account_stability': 0.05
            }
            
            final_score = sum(
                risk_factors[factor] * weights[factor]
                for factor in weights.keys()
                if factor in risk_factors
            )
            
            # Determine risk category
            if final_score >= 80:
                risk_category = "Very Low Risk"
                risk_color = "green"
            elif final_score >= 65:
                risk_category = "Low Risk"
                risk_color = "lightgreen"
            elif final_score >= 50:
                risk_category = "Medium Risk"
                risk_color = "yellow"
            elif final_score >= 35:
                risk_category = "High Risk"
                risk_color = "orange"
            else:
                risk_category = "Very High Risk"
                risk_color = "red"
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(risk_factors, final_score)
            
            return {
                "customer_id": customer_id,
                "customer_name": f"{customer.first_name} {customer.last_name}",
                "risk_score": round(final_score, 2),
                "risk_category": risk_category,
                "risk_color": risk_color,
                "risk_factors": risk_factors,
                "factor_weights": weights,
                "recommendations": recommendations,
                "calculated_at": datetime.utcnow().isoformat(),
                "next_review_date": (date.today() + timedelta(days=30)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score for customer {customer_id}: {e}")
            return {"error": str(e)}
    
    def _analyze_payment_history(self, customer_id: int) -> float:
        """Analyze customer's payment history (40% of total score)"""
        try:
            # Get all payments for this customer
            payments = self.db.query(Payment).join(Loan).filter(
                Loan.borrower_id == customer_id,
                Payment.status == "confirmed"
            ).all()
            
            if not payments:
                return 50.0  # Neutral score for new customers
            
            # Calculate metrics
            total_payments = len(payments)
            on_time_payments = 0
            late_payments = 0
            early_payments = 0
            
            for payment in payments:
                loan = payment.loan
                if payment.payment_date <= loan.next_payment_date:
                    if payment.payment_date < loan.next_payment_date:
                        early_payments += 1
                    on_time_payments += 1
                else:
                    late_payments += 1
            
            # Calculate payment punctuality score (0-100)
            punctuality_score = (on_time_payments / total_payments) * 100
            
            # Bonus for early payments
            early_bonus = min((early_payments / total_payments) * 10, 10)
            
            # Penalty for late payments
            late_penalty = (late_payments / total_payments) * 20
            
            # Get arrears history
            arrears_count = self.db.query(Arrear).join(Loan).filter(
                Loan.borrower_id == customer_id
            ).count()
            
            arrears_penalty = min(arrears_count * 5, 25)  # Max 25 point penalty
            
            final_score = min(100, max(0, punctuality_score + early_bonus - late_penalty - arrears_penalty))
            
            return final_score
            
        except Exception as e:
            logger.error(f"Error analyzing payment history: {e}")
            return 50.0
    
    def _analyze_savings_behavior(self, customer_id: int) -> float:
        """Analyze customer's savings behavior and consistency"""
        try:
            from app.models.loan import Transaction
            
            savings_account = self.db.query(SavingsAccount).filter(
                SavingsAccount.user_id == customer_id
            ).first()
            
            if not savings_account:
                return 30.0  # Low score if no savings account
            
            # Current balance score (0-40 points)
            balance_score = min((float(savings_account.balance) / 10000) * 40, 40)
            
            # Savings consistency score (0-30 points)
            savings_transactions = self.db.query(Transaction).filter(
                Transaction.user_id == customer_id,
                Transaction.account_type == "savings",
                Transaction.transaction_type == "deposit",
                Transaction.created_at >= datetime.utcnow() - timedelta(days=180)  # Last 6 months
            ).all()
            
            if len(savings_transactions) >= 6:  # Regular saver
                consistency_score = 30
            elif len(savings_transactions) >= 3:  # Moderate saver
                consistency_score = 20
            elif len(savings_transactions) >= 1:  # Occasional saver
                consistency_score = 10
            else:  # No savings activity
                consistency_score = 0
            
            # Registration fee payment score (0-20 points)
            registration_score = 20 if savings_account.registration_fee_paid else 0
            
            # Growth trend score (0-10 points)
            if len(savings_transactions) >= 2:
                amounts = [float(tx.amount) for tx in savings_transactions[-6:]]  # Last 6 transactions
                if len(amounts) >= 2:
                    trend = np.polyfit(range(len(amounts)), amounts, 1)[0]  # Linear trend
                    growth_score = min(max(trend / 100, 0), 10)  # Normalize to 0-10
                else:
                    growth_score = 5
            else:
                growth_score = 5
            
            total_score = balance_score + consistency_score + registration_score + growth_score
            return min(100, total_score)
            
        except Exception as e:
            logger.error(f"Error analyzing savings behavior: {e}")
            return 40.0
    
    def _analyze_loan_utilization(self, customer_id: int) -> float:
        """Analyze how customer utilizes their loan capacity"""
        try:
            savings_account = self.db.query(SavingsAccount).filter(
                SavingsAccount.user_id == customer_id
            ).first()
            
            if not savings_account:
                return 30.0
            
            # Get active loans
            active_loans = self.db.query(Loan).filter(
                Loan.borrower_id == customer_id,
                Loan.status.in_(["active", "arrears"])
            ).all()
            
            loan_limit = float(savings_account.loan_limit)
            total_loan_balance = sum(float(loan.balance) for loan in active_loans)
            
            if loan_limit <= 0:
                return 50.0  # Neutral score
            
            # Utilization ratio
            utilization_ratio = total_loan_balance / loan_limit
            
            # Optimal utilization is 30-70%
            if 0.3 <= utilization_ratio <= 0.7:
                utilization_score = 100  # Optimal range
            elif utilization_ratio < 0.3:
                utilization_score = 70 + (utilization_ratio / 0.3) * 30  # Under-utilized
            elif utilization_ratio <= 0.9:
                utilization_score = 100 - ((utilization_ratio - 0.7) / 0.2) * 30  # Over-utilized
            else:
                utilization_score = 40 - ((utilization_ratio - 0.9) / 0.1) * 40  # Highly over-utilized
            
            # Loan diversity bonus (having multiple smaller loans vs one large loan)
            if len(active_loans) > 1 and len(active_loans) <= 3:
                diversity_bonus = 10
            else:
                diversity_bonus = 0
            
            # Completed loans bonus
            completed_loans = self.db.query(Loan).filter(
                Loan.borrower_id == customer_id,
                Loan.status == "completed"
            ).count()
            
            completion_bonus = min(completed_loans * 2, 15)  # Max 15 points
            
            final_score = min(100, utilization_score + diversity_bonus + completion_bonus)
            return max(0, final_score)
            
        except Exception as e:
            logger.error(f"Error analyzing loan utilization: {e}")
            return 50.0
    
    def _analyze_group_performance(self, customer_id: int) -> float:
        """Analyze performance of customer's group"""
        try:
            # Get customer's group
            membership = self.db.query(GroupMembership).filter(
                GroupMembership.member_id == customer_id,
                GroupMembership.is_active == True
            ).first()
            
            if not membership:
                return 50.0  # Neutral score if not in group
            
            group = membership.group
            
            # Get all group members
            group_members = self.db.query(GroupMembership).filter(
                GroupMembership.group_id == group.id,
                GroupMembership.is_active == True
            ).all()
            
            member_ids = [gm.member_id for gm in group_members]
            
            # Analyze group loan performance
            group_loans = self.db.query(Loan).filter(
                Loan.borrower_id.in_(member_ids)
            ).all()
            
            if not group_loans:
                return 60.0  # Slightly above neutral for new groups
            
            # Calculate group metrics
            completed_loans = len([loan for loan in group_loans if loan.status == "completed"])
            arrears_loans = len([loan for loan in group_loans if loan.status == "arrears"])
            total_loans = len(group_loans)
            
            # Group completion rate
            completion_rate = (completed_loans / total_loans) * 100 if total_loans > 0 else 0
            
            # Group arrears rate
            arrears_rate = (arrears_loans / total_loans) * 100 if total_loans > 0 else 0
            
            # Calculate score
            base_score = completion_rate
            arrears_penalty = arrears_rate * 2  # Double penalty for arrears
            
            # Group savings performance
            group_savings = self.db.query(SavingsAccount).filter(
                SavingsAccount.user_id.in_(member_ids)
            ).all()
            
            total_group_savings = sum(float(acc.balance) for acc in group_savings)
            avg_savings_per_member = total_group_savings / len(group_members) if group_members else 0
            
            # Savings bonus (0-20 points)
            savings_bonus = min((avg_savings_per_member / 5000) * 20, 20)
            
            final_score = min(100, max(0, base_score - arrears_penalty + savings_bonus))
            return final_score
            
        except Exception as e:
            logger.error(f"Error analyzing group performance: {e}")
            return 50.0
    
    def _analyze_account_stability(self, customer_id: int) -> float:
        """Analyze account stability and activity patterns"""
        try:
            from app.models.loan import Transaction
            
            # Get account age
            customer = self.db.query(User).filter(User.id == customer_id).first()
            if not customer:
                return 30.0
            
            account_age_days = (datetime.utcnow() - customer.created_at).days
            
            # Age bonus (0-30 points) - older accounts are more stable
            age_score = min((account_age_days / 365) * 30, 30)
            
            # Transaction frequency analysis (0-40 points)
            recent_transactions = self.db.query(Transaction).filter(
                Transaction.user_id == customer_id,
                Transaction.created_at >= datetime.utcnow() - timedelta(days=90)
            ).all()
            
            transaction_frequency = len(recent_transactions) / 12  # Transactions per week
            frequency_score = min(transaction_frequency * 10, 40)
            
            # Account balance stability (0-30 points)
            savings_account = customer.savings_account
            if savings_account:
                current_balance = float(savings_account.balance)
                
                # Get balance history over last 3 months
                balance_transactions = self.db.query(Transaction).filter(
                    Transaction.user_id == customer_id,
                    Transaction.account_type == "savings",
                    Transaction.created_at >= datetime.utcnow() - timedelta(days=90)
                ).order_by(Transaction.created_at.asc()).all()
                
                if len(balance_transactions) >= 3:
                    balances = [float(tx.balance_after) for tx in balance_transactions]
                    balance_variance = np.var(balances)
                    
                    # Lower variance = more stable = higher score
                    stability_score = max(0, 30 - (balance_variance / 1000000) * 30)
                else:
                    stability_score = 15  # Moderate score for insufficient data
            else:
                stability_score = 0
            
            total_score = age_score + frequency_score + stability_score
            return min(100, total_score)
            
        except Exception as e:
            logger.error(f"Error analyzing account stability: {e}")
            return 40.0
    
    def _generate_risk_recommendations(self, risk_factors: Dict[str, float], 
                                     total_score: float) -> List[str]:
        """Generate AI-powered recommendations based on risk analysis"""
        recommendations = []
        
        if risk_factors.get('payment_history', 0) < 60:
            recommendations.append("🚨 Improve payment punctuality - set up automatic payments")
            recommendations.append("📅 Consider shorter loan terms to build payment history")
        
        if risk_factors.get('savings_behavior', 0) < 50:
            recommendations.append("💰 Increase regular savings deposits to improve loan capacity")
            recommendations.append("🎯 Set savings goals - target 10% of income monthly")
        
        if risk_factors.get('loan_utilization', 0) < 40:
            recommendations.append("⚖️ Better loan management needed - avoid over-borrowing")
            recommendations.append("📊 Consider debt consolidation if multiple active loans")
        
        if risk_factors.get('group_performance', 0) < 45:
            recommendations.append("👥 Work with group members to improve collective performance")
            recommendations.append("🤝 Consider group financial literacy training")
        
        if total_score < 50:
            recommendations.append("🎓 Attend financial literacy workshops")
            recommendations.append("💡 Start with smaller loan amounts to build trust")
            recommendations.append("🔄 Focus on loan completion before new applications")
        
        if not recommendations:
            recommendations.append("🏆 Excellent financial behavior - consider premium loan products")
            recommendations.append("💎 Eligible for loyalty benefits and reduced rates")
        
        return recommendations
    
    # ==================== PREDICTIVE ANALYTICS ====================
    
    def forecast_arrears_risk(self, days_ahead: int = 30, branch_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Predict which loans are likely to go into arrears using machine learning
        """
        try:
            # Get active loans
            query = self.db.query(Loan).filter(
                Loan.status == "active",
                Loan.balance > 0
            )
            
            if branch_id:
                branch_users = self.db.query(User).filter(
                    User.branch_id == branch_id,
                    User.role == UserRole.CUSTOMER
                ).all()
                user_ids = [u.id for u in branch_users]
                query = query.filter(Loan.borrower_id.in_(user_ids))
            
            active_loans = query.all()
            
            predictions = []
            high_risk_loans = []
            medium_risk_loans = []
            low_risk_loans = []
            
            for loan in active_loans:
                # Calculate risk score for this loan
                customer_risk = self.calculate_customer_risk_score(loan.borrower_id)
                risk_score = customer_risk.get('risk_score', 50)
                
                # Additional loan-specific factors
                days_to_due = (loan.due_date - date.today()).days
                payment_ratio = float(loan.amount_paid) / float(loan.total_amount)
                
                # Calculate arrears probability
                if risk_score < 40:
                    arrears_probability = 0.8 + (0.2 * (1 - payment_ratio))
                elif risk_score < 60:
                    arrears_probability = 0.5 + (0.3 * (1 - payment_ratio))
                else:
                    arrears_probability = 0.2 + (0.3 * (1 - payment_ratio))
                
                # Adjust for time to due date
                if days_to_due <= 7:
                    arrears_probability *= 1.5
                elif days_to_due <= 30:
                    arrears_probability *= 1.2
                
                arrears_probability = min(1.0, arrears_probability)
                
                loan_prediction = {
                    "loan_id": loan.id,
                    "loan_number": loan.loan_number,
                    "borrower_name": f"{loan.borrower.first_name} {loan.borrower.last_name}",
                    "balance": float(loan.balance),
                    "due_date": loan.due_date.isoformat(),
                    "days_to_due": days_to_due,
                    "customer_risk_score": risk_score,
                    "arrears_probability": round(arrears_probability * 100, 1),
                    "payment_progress": round(payment_ratio * 100, 1)
                }
                
                predictions.append(loan_prediction)
                
                # Categorize risk
                if arrears_probability >= 0.7:
                    high_risk_loans.append(loan_prediction)
                elif arrears_probability >= 0.4:
                    medium_risk_loans.append(loan_prediction)
                else:
                    low_risk_loans.append(loan_prediction)
            
            # Calculate total amounts at risk
            high_risk_amount = sum(pred["balance"] for pred in high_risk_loans)
            medium_risk_amount = sum(pred["balance"] for pred in medium_risk_loans)
            
            return {
                "forecast_period_days": days_ahead,
                "total_loans_analyzed": len(active_loans),
                "predictions": predictions,
                "risk_categories": {
                    "high_risk": {
                        "count": len(high_risk_loans),
                        "total_amount": high_risk_amount,
                        "loans": high_risk_loans
                    },
                    "medium_risk": {
                        "count": len(medium_risk_loans),
                        "total_amount": medium_risk_amount,
                        "loans": medium_risk_loans
                    },
                    "low_risk": {
                        "count": len(low_risk_loans),
                        "loans": low_risk_loans
                    }
                },
                "summary": {
                    "total_amount_at_risk": high_risk_amount + medium_risk_amount,
                    "high_risk_percentage": round((len(high_risk_loans) / len(active_loans)) * 100, 1) if active_loans else 0,
                    "predicted_arrears_amount": high_risk_amount * 0.8 + medium_risk_amount * 0.3
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error forecasting arrears risk: {e}")
            return {"error": str(e)}
    
    def analyze_seasonal_patterns(self, branch_id: Optional[int] = None) -> Dict[str, Any]:
        """Analyze seasonal patterns in loans and payments"""
        try:
            # Get historical data (last 2 years)
            start_date = datetime.utcnow() - timedelta(days=730)
            
            query = self.db.query(Loan).filter(Loan.created_at >= start_date)
            
            if branch_id:
                branch_users = self.db.query(User).filter(
                    User.branch_id == branch_id,
                    User.role == UserRole.CUSTOMER
                ).all()
                user_ids = [u.id for u in branch_users]
                query = query.filter(Loan.borrower_id.in_(user_ids))
            
            loans = query.all()
            
            # Group by month
            monthly_data = {}
            for month in range(1, 13):
                monthly_loans = [loan for loan in loans if loan.created_at.month == month]
                monthly_amount = sum(float(loan.total_amount) for loan in monthly_loans)
                
                # Get payment data for this month
                monthly_payments = self.db.query(Payment).join(Loan).filter(
                    extract('month', Payment.payment_date) == month,
                    Payment.status == "confirmed"
                ).all()
                
                if branch_id:
                    monthly_payments = [p for p in monthly_payments if p.loan.borrower_id in user_ids]
                
                monthly_payment_amount = sum(float(payment.amount) for payment in monthly_payments)
                
                monthly_data[month] = {
                    "month": month,
                    "month_name": datetime(2024, month, 1).strftime('%B'),
                    "loan_count": len(monthly_loans),
                    "loan_amount": monthly_amount,
                    "payment_count": len(monthly_payments),
                    "payment_amount": monthly_payment_amount,
                    "collection_rate": (monthly_payment_amount / monthly_amount * 100) if monthly_amount > 0 else 0
                }
            
            # Identify peak and low seasons
            loan_amounts_by_month = [data["loan_amount"] for data in monthly_data.values()]
            peak_month = max(monthly_data.keys(), key=lambda m: monthly_data[m]["loan_amount"])
            low_month = min(monthly_data.keys(), key=lambda m: monthly_data[m]["loan_amount"])
            
            return {
                "monthly_breakdown": list(monthly_data.values()),
                "peak_season": {
                    "month": peak_month,
                    "month_name": monthly_data[peak_month]["month_name"],
                    "loan_amount": monthly_data[peak_month]["loan_amount"]
                },
                "low_season": {
                    "month": low_month,
                    "month_name": monthly_data[low_month]["month_name"],
                    "loan_amount": monthly_data[low_month]["loan_amount"]
                },
                "average_monthly_loans": np.mean(loan_amounts_by_month),
                "seasonality_index": (max(loan_amounts_by_month) / min(loan_amounts_by_month)) if min(loan_amounts_by_month) > 0 else 1,
                "analysis_period": "Last 24 months",
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing seasonal patterns: {e}")
            return {"error": str(e)}
    
    # ==================== PERFORMANCE ANALYTICS ====================
    
    def get_branch_performance_ranking(self) -> List[Dict[str, Any]]:
        """Rank all branches by performance metrics"""
        try:
            branches = self.db.query(Branch).filter(Branch.is_active == True).all()
            
            branch_performance = []
            
            for branch in branches:
                # Get branch customers
                branch_customers = self.db.query(User).filter(
                    User.branch_id == branch.id,
                    User.role == UserRole.CUSTOMER
                ).all()
                
                customer_ids = [c.id for c in branch_customers]
                
                if not customer_ids:
                    continue
                
                # Calculate branch metrics
                metrics = self._calculate_branch_kpis(branch.id)
                
                # Calculate performance score
                performance_score = (
                    metrics['collection_rate'] * 0.4 +
                    metrics['growth_rate'] * 0.3 +
                    min(metrics['profit_margin'], 50) * 0.2 +  # Cap profit margin at 50%
                    (100 - metrics['arrears_rate']) * 0.1
                )
                
                branch_data = {
                    "branch_id": branch.id,
                    "branch_name": branch.name,
                    "branch_code": branch.code,
                    "manager_name": f"{branch.manager.first_name} {branch.manager.last_name}" if branch.manager else "No Manager",
                    "performance_score": round(performance_score, 2),
                    "collection_rate": round(metrics['collection_rate'], 2),
                    "growth_rate": round(metrics['growth_rate'], 2),
                    "profit_margin": round(metrics['profit_margin'], 2),
                    "arrears_rate": round(metrics['arrears_rate'], 2),
                    "total_customers": metrics['total_customers'],
                    "active_loans": metrics['active_loans'],
                    "total_portfolio": metrics['total_portfolio']
                }
                
                branch_performance.append(branch_data)
            
            # Sort by performance score
            branch_performance.sort(key=lambda x: x['performance_score'], reverse=True)
            
            # Add rankings
            for i, branch in enumerate(branch_performance):
                branch['rank'] = i + 1
                branch['performance_grade'] = self._get_performance_grade(branch['performance_score'])
            
            return branch_performance
            
        except Exception as e:
            logger.error(f"Error ranking branch performance: {e}")
            return []
    
    def get_loan_officer_performance(self, branch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Analyze and rank loan officer performance"""
        try:
            # Get loan officers
            query = self.db.query(User).filter(
                User.role == UserRole.LOAN_OFFICER,
                User.is_active == True
            )
            
            if branch_id:
                query = query.filter(User.branch_id == branch_id)
            
            loan_officers = query.all()
            
            officer_performance = []
            
            for officer in loan_officers:
                # Get officer's groups
                officer_groups = self.db.query(Group).filter(
                    Group.loan_officer_id == officer.id,
                    Group.is_active == True
                ).all()
                
                if not officer_groups:
                    continue
                
                # Get all members from officer's groups
                group_ids = [g.id for g in officer_groups]
                group_members = self.db.query(GroupMembership).filter(
                    GroupMembership.group_id.in_(group_ids),
                    GroupMembership.is_active == True
                ).all()
                
                member_ids = [gm.member_id for gm in group_members]
                
                if not member_ids:
                    continue
                
                # Calculate officer metrics
                total_customers = len(member_ids)
                
                # Loan metrics
                officer_loans = self.db.query(Loan).filter(
                    Loan.borrower_id.in_(member_ids)
                ).all()
                
                active_loans = [loan for loan in officer_loans if loan.status == "active"]
                completed_loans = [loan for loan in officer_loans if loan.status == "completed"]
                arrears_loans = [loan for loan in officer_loans if loan.status == "arrears"]
                
                # Collection metrics
                total_disbursed = sum(float(loan.total_amount) for loan in officer_loans)
                total_collected = sum(float(loan.amount_paid) for loan in officer_loans)
                collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 0
                
                # Savings metrics
                officer_savings = self.db.query(SavingsAccount).filter(
                    SavingsAccount.user_id.in_(member_ids)
                ).all()
                
                total_savings = sum(float(acc.balance) for acc in officer_savings)
                avg_savings_per_customer = total_savings / total_customers if total_customers > 0 else 0
                
                # Performance score calculation
                performance_score = (
                    collection_rate * 0.5 +
                    min((len(completed_loans) / len(officer_loans)) * 100, 100) * 0.3 +
                    min((avg_savings_per_customer / 5000) * 100, 100) * 0.2
                ) if officer_loans else 0
                
                officer_data = {
                    "officer_id": officer.id,
                    "officer_name": f"{officer.first_name} {officer.last_name}",
                    "branch_name": officer.branch.name if officer.branch else "No Branch",
                    "performance_score": round(performance_score, 2),
                    "total_customers": total_customers,
                    "total_groups": len(officer_groups),
                    "active_loans": len(active_loans),
                    "completed_loans": len(completed_loans),
                    "arrears_loans": len(arrears_loans),
                    "collection_rate": round(collection_rate, 2),
                    "total_portfolio": total_disbursed,
                    "total_savings_mobilized": total_savings,
                    "avg_savings_per_customer": round(avg_savings_per_customer, 2)
                }
                
                officer_performance.append(officer_data)
            
            # Sort by performance score
            officer_performance.sort(key=lambda x: x['performance_score'], reverse=True)
            
            # Add rankings
            for i, officer in enumerate(officer_performance):
                officer['rank'] = i + 1
                officer['performance_grade'] = self._get_performance_grade(officer['performance_score'])
            
            return officer_performance
            
        except Exception as e:
            logger.error(f"Error analyzing loan officer performance: {e}")
            return []
    
    def _calculate_branch_kpis(self, branch_id: int) -> Dict[str, float]:
        """Calculate key performance indicators for a branch"""
        try:
            # Get branch customers
            branch_customers = self.db.query(User).filter(
                User.branch_id == branch_id,
                User.role == UserRole.CUSTOMER
            ).all()
            
            customer_ids = [c.id for c in branch_customers]
            
            # Loan metrics
            branch_loans = self.db.query(Loan).filter(
                Loan.borrower_id.in_(customer_ids)
            ).all()
            
            active_loans = [loan for loan in branch_loans if loan.status == "active"]
            completed_loans = [loan for loan in branch_loans if loan.status == "completed"]
            arrears_loans = [loan for loan in branch_loans if loan.status == "arrears"]
            
            # Financial metrics
            total_disbursed = sum(float(loan.total_amount) for loan in branch_loans)
            total_collected = sum(float(loan.amount_paid) for loan in branch_loans)
            total_outstanding = sum(float(loan.balance) for loan in active_loans + arrears_loans)
            
            collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 0
            arrears_rate = (len(arrears_loans) / len(branch_loans) * 100) if branch_loans else 0
            
            # Growth rate (compare last 3 months vs previous 3 months)
            three_months_ago = datetime.utcnow() - timedelta(days=90)
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            
            recent_loans = [loan for loan in branch_loans if loan.created_at >= three_months_ago]
            previous_loans = [loan for loan in branch_loans if six_months_ago <= loan.created_at < three_months_ago]
            
            recent_amount = sum(float(loan.total_amount) for loan in recent_loans)
            previous_amount = sum(float(loan.total_amount) for loan in previous_loans)
            
            growth_rate = ((recent_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0
            
            # Profit margin (admin only calculation)
            from app.models.loan import LoanProduct, BranchInventory
            
            branch_inventory = self.db.query(BranchInventory).filter(
                BranchInventory.branch_id == branch_id
            ).all()
            
            total_buying_value = sum(
                float(item.loan_product.buying_price) * item.current_quantity
                for item in branch_inventory
            )
            
            total_selling_value = sum(
                float(item.loan_product.selling_price) * item.current_quantity
                for item in branch_inventory
            )
            
            profit_margin = ((total_selling_value - total_buying_value) / total_buying_value * 100) if total_buying_value > 0 else 0
            
            return {
                "total_customers": len(branch_customers),
                "active_loans": len(active_loans),
                "completed_loans": len(completed_loans),
                "arrears_loans": len(arrears_loans),
                "collection_rate": collection_rate,
                "arrears_rate": arrears_rate,
                "growth_rate": growth_rate,
                "profit_margin": profit_margin,
                "total_portfolio": total_outstanding,
                "total_disbursed": total_disbursed,
                "total_collected": total_collected
            }
            
        except Exception as e:
            logger.error(f"Error calculating branch KPIs: {e}")
            return {}
    
    def _get_performance_grade(self, score: float) -> str:
        """Convert performance score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        else:
            return "D"


# Initialize analytics engine
analytics_engine = AdvancedAnalyticsEngine()