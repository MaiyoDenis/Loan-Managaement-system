"""
AI-Powered Risk Scoring Engine for Loan Applications
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

from app.database import SessionLocal
from app.models.user import User
from app.models.loan import Loan, Payment, SavingsAccount, RiskScore
from app.models.branch import Group, GroupMembership


class RiskScoringEngine:
    """AI-powered risk scoring engine for loan applications"""
    
    def __init__(self):
        self.model_path = "models/risk_model.joblib"
        self.scaler_path = "models/risk_scaler.joblib"
        self.model = None
        self.scaler = None
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
        else:
            self._create_initial_model()
    
    def _create_initial_model(self):
        """Create initial risk scoring model"""
        # Create directories
        os.makedirs("models", exist_ok=True)
        
        # Initialize with default model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.scaler = StandardScaler()
        
        # Save initial model
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
    
    def calculate_risk_score(self, user_id: int) -> Dict[str, Any]:
        """Calculate comprehensive risk score for a user"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Extract features
            features = self._extract_user_features(db, user)
            
            # Calculate individual factor scores
            payment_history_score = self._calculate_payment_history_score(db, user)
            savings_behavior_score = self._calculate_savings_behavior_score(db, user)
            group_performance_score = self._calculate_group_performance_score(db, user)
            loan_utilization_score = self._calculate_loan_utilization_score(db, user)
            tenure_score = self._calculate_tenure_score(user)
            
            # Weighted composite score
            weights = {
                'payment_history': 0.35,
                'savings_behavior': 0.25,
                'group_performance': 0.20,
                'loan_utilization': 0.15,
                'tenure': 0.05
            }
            
            composite_score = (
                payment_history_score * weights['payment_history'] +
                savings_behavior_score * weights['savings_behavior'] +
                group_performance_score * weights['group_performance'] +
                loan_utilization_score * weights['loan_utilization'] +
                tenure_score * weights['tenure']
            )
            
            # Normalize to 0-100 scale
            final_score = max(0, min(100, composite_score))
            
            # Determine risk category
            risk_category = self._get_risk_category(final_score)
            
            # Store risk score
            risk_score = RiskScore(
                user_id=user_id,
                score=Decimal(str(round(final_score, 2))),
                factors={
                    'payment_history': round(payment_history_score, 2),
                    'savings_behavior': round(savings_behavior_score, 2),
                    'group_performance': round(group_performance_score, 2),
                    'loan_utilization': round(loan_utilization_score, 2),
                    'tenure': round(tenure_score, 2),
                    'weights': weights,
                    'features': features
                }
            )
            
            db.add(risk_score)
            db.commit()
            
            return {
                "user_id": user_id,
                "risk_score": round(final_score, 2),
                "risk_category": risk_category,
                "factors": {
                    "payment_history": {
                        "score": round(payment_history_score, 2),
                        "weight": weights['payment_history'],
                        "contribution": round(payment_history_score * weights['payment_history'], 2)
                    },
                    "savings_behavior": {
                        "score": round(savings_behavior_score, 2),
                        "weight": weights['savings_behavior'],
                        "contribution": round(savings_behavior_score * weights['savings_behavior'], 2)
                    },
                    "group_performance": {
                        "score": round(group_performance_score, 2),
                        "weight": weights['group_performance'],
                        "contribution": round(group_performance_score * weights['group_performance'], 2)
                    },
                    "loan_utilization": {
                        "score": round(loan_utilization_score, 2),
                        "weight": weights['loan_utilization'],
                        "contribution": round(loan_utilization_score * weights['loan_utilization'], 2)
                    },
                    "tenure": {
                        "score": round(tenure_score, 2),
                        "weight": weights['tenure'],
                        "contribution": round(tenure_score * weights['tenure'], 2)
                    }
                },
                "recommendations": self._get_risk_recommendations(final_score, features)
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()
    
    def _extract_user_features(self, db: Session, user: User) -> Dict[str, Any]:
        """Extract features for risk scoring"""
        features = {}
        
        # User tenure (days since registration)
        tenure_days = (datetime.utcnow() - user.created_at).days
        features['tenure_days'] = tenure_days
        
        # Savings account metrics
        if user.savings_account:
            features['current_savings'] = float(user.savings_account.balance)
            features['registration_fee_paid'] = user.savings_account.registration_fee_paid
            features['loan_limit'] = float(user.savings_account.loan_limit)
        else:
            features['current_savings'] = 0.0
            features['registration_fee_paid'] = False
            features['loan_limit'] = 0.0
        
        # Loan history
        all_loans = db.query(Loan).filter(Loan.borrower_id == user.id).all()
        features['total_loans'] = len(all_loans)
        features['active_loans'] = len([l for l in all_loans if l.status == 'active'])
        features['completed_loans'] = len([l for l in all_loans if l.status == 'completed'])
        features['defaulted_loans'] = len([l for l in all_loans if l.status == 'defaulted'])
        
        # Payment behavior
        all_payments = db.query(Payment).join(Loan).filter(
            Loan.borrower_id == user.id,
            Payment.status == 'confirmed'
        ).all()
        features['total_payments'] = len(all_payments)
        features['avg_payment_amount'] = np.mean([float(p.amount) for p in all_payments]) if all_payments else 0
        
        # Calculate payment punctuality
        on_time_payments = 0
        late_payments = 0
        
        for payment in all_payments:
            loan = payment.loan
            if loan.loan_type.allows_partial_payments:
                # For partial payments, check if paid within grace period
                if payment.payment_date <= loan.next_payment_date:
                    on_time_payments += 1
                else:
                    late_payments += 1
            else:
                # For full payments, check against due date
                if payment.payment_date <= loan.due_date:
                    on_time_payments += 1
                else:
                    late_payments += 1
        
        features['on_time_payments'] = on_time_payments
        features['late_payments'] = late_payments
        features['payment_punctuality'] = (on_time_payments / (on_time_payments + late_payments)) if (on_time_payments + late_payments) > 0 else 1.0
        
        # Group performance influence
        group_membership = db.query(GroupMembership).filter(
            GroupMembership.member_id == user.id,
            GroupMembership.is_active == True
        ).first()
        
        if group_membership:
            group_stats = self._calculate_group_statistics(db, group_membership.group_id)
            features['group_default_rate'] = group_stats['default_rate']
            features['group_avg_savings'] = group_stats['avg_savings']
            features['group_collection_rate'] = group_stats['collection_rate']
        else:
            features['group_default_rate'] = 0.0
            features['group_avg_savings'] = 0.0
            features['group_collection_rate'] = 100.0
        
        return features
    
    def _calculate_payment_history_score(self, db: Session, user: User) -> float:
        """Calculate payment history score (0-100)"""
        # Get payment history
        payments = db.query(Payment).join(Loan).filter(
            Loan.borrower_id == user.id,
            Payment.status == 'confirmed'
        ).all()
        
        if not payments:
            return 70.0  # Neutral score for new customers
        
        # Calculate payment metrics
        total_payments = len(payments)
        on_time_payments = 0
        early_payments = 0
        late_payments = 0
        
        for payment in payments:
            loan = payment.loan
            if payment.payment_date <= loan.due_date:
                if payment.payment_date < loan.due_date:
                    early_payments += 1
                on_time_payments += 1
            else:
                late_payments += 1
        
        # Score calculation
        punctuality_rate = on_time_payments / total_payments
        early_payment_bonus = (early_payments / total_payments) * 10
        
        score = (punctuality_rate * 90) + early_payment_bonus
        
        # Penalty for defaults
        defaulted_loans = db.query(Loan).filter(
            Loan.borrower_id == user.id,
            Loan.status == 'defaulted'
        ).count()
        
        default_penalty = defaulted_loans * 25
        
        return max(0, min(100, score - default_penalty))
    
    def _calculate_savings_behavior_score(self, db: Session, user: User) -> float:
        """Calculate savings behavior score (0-100)"""
        if not user.savings_account:
            return 20.0
        
        savings_account = user.savings_account
        
        # Base score from current savings
        current_savings = float(savings_account.balance)
        savings_score = min(50, (current_savings / 1000) * 10)  # Max 50 points for 5000+ savings
        
        # Registration fee payment bonus
        if savings_account.registration_fee_paid:
            registration_bonus = 20
        else:
            registration_bonus = 0
        
        # Savings consistency (analyze transaction history)
        from app.models.loan import Transaction
        savings_transactions = db.query(Transaction).filter(
            Transaction.user_id == user.id,
            Transaction.account_type == 'savings',
            Transaction.transaction_type == 'deposit'
        ).order_by(Transaction.created_at.desc()).limit(10).all()
        
        if len(savings_transactions) >= 3:
            # Calculate consistency bonus
            amounts = [float(tx.amount) for tx in savings_transactions]
            consistency = 1 / (1 + np.std(amounts) / np.mean(amounts))  # Lower variance = higher consistency
            consistency_bonus = consistency * 20
        else:
            consistency_bonus = 10  # Neutral for insufficient data
        
        # Account age bonus
        account_age_days = (datetime.utcnow() - savings_account.created_at).days
        age_bonus = min(10, account_age_days / 30)  # Max 10 points for 30+ days
        
        total_score = savings_score + registration_bonus + consistency_bonus + age_bonus
        return max(0, min(100, total_score))
    
    def _calculate_group_performance_score(self, db: Session, user: User) -> float:
        """Calculate group performance influence score (0-100)"""
        membership = db.query(GroupMembership).filter(
            GroupMembership.member_id == user.id,
            GroupMembership.is_active == True
        ).first()
        
        if not membership:
            return 50.0  # Neutral score
        
        group_stats = self._calculate_group_statistics(db, membership.group_id)
        
        # Score based on group performance
        collection_rate = group_stats['collection_rate']
        default_rate = group_stats['default_rate']
        avg_savings = group_stats['avg_savings']
        
        # Collection rate contribution (40 points max)
        collection_score = (collection_rate / 100) * 40
        
        # Default rate penalty (30 points max penalty)
        default_penalty = default_rate * 30
        
        # Group savings strength (20 points max)
        savings_score = min(20, (avg_savings / 5000) * 20)
        
        # Group tenure bonus (10 points max)
        group_age_days = (datetime.utcnow() - membership.group.created_at).days
        tenure_bonus = min(10, group_age_days / 60)  # Max points for 60+ days
        
        total_score = collection_score - default_penalty + savings_score + tenure_bonus
        return max(0, min(100, total_score))
    
    def _calculate_loan_utilization_score(self, db: Session, user: User) -> float:
        """Calculate loan utilization score (0-100)"""
        if not user.savings_account:
            return 30.0
        
        active_loans = db.query(Loan).filter(
            Loan.borrower_id == user.id,
            Loan.status.in_(['active', 'arrears'])
        ).all()
        
        if not active_loans:
            return 80.0  # Good score for no active loans
        
        # Calculate utilization metrics
        total_loan_balance = sum(float(loan.balance) for loan in active_loans)
        loan_limit = float(user.savings_account.loan_limit)
        
        if loan_limit <= 0:
            return 20.0
        
        utilization_rate = total_loan_balance / loan_limit
        
        # Optimal utilization is around 30-50%
        if utilization_rate <= 0.3:
            utilization_score = 100 - (0.3 - utilization_rate) * 50  # Penalty for under-utilization
        elif utilization_rate <= 0.5:
            utilization_score = 100  # Optimal range
        elif utilization_rate <= 0.8:
            utilization_score = 100 - (utilization_rate - 0.5) * 100  # Linear penalty
        else:
            utilization_score = 100 - (utilization_rate - 0.5) * 150  # Higher penalty for over-utilization
        
        # Number of active loans factor
        loan_count_factor = max(0.5, 1 - (len(active_loans) - 1) * 0.2)  # Penalty for too many loans
        
        final_score = utilization_score * loan_count_factor
        return max(0, min(100, final_score))
    
    def _calculate_tenure_score(self, user: User) -> float:
        """Calculate tenure score based on account age (0-100)"""
        account_age_days = (datetime.utcnow() - user.created_at).days
        
        if account_age_days < 30:
            return 20.0  # New customer
        elif account_age_days < 90:
            return 40.0  # Recent customer
        elif account_age_days < 180:
            return 60.0  # Established customer
        elif account_age_days < 365:
            return 80.0  # Long-term customer
        else:
            return 100.0  # Loyal customer
    
    def _calculate_group_statistics(self, db: Session, group_id: int) -> Dict[str, float]:
        """Calculate group performance statistics"""
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"collection_rate": 0.0, "default_rate": 100.0, "avg_savings": 0.0}
        
        # Get all group members
        memberships = db.query(GroupMembership).filter(
            GroupMembership.group_id == group_id,
            GroupMembership.is_active == True
        ).all()
        
        member_ids = [m.member_id for m in memberships]
        
        if not member_ids:
            return {"collection_rate": 0.0, "default_rate": 0.0, "avg_savings": 0.0}
        
        # Get all loans for group members
        group_loans = db.query(Loan).filter(Loan.borrower_id.in_(member_ids)).all()
        
        if not group_loans:
            # Calculate average savings for members without loans
            savings_accounts = db.query(SavingsAccount).filter(
                SavingsAccount.user_id.in_(member_ids)
            ).all()
            
            avg_savings = np.mean([float(acc.balance) for acc in savings_accounts]) if savings_accounts else 0.0
            
            return {"collection_rate": 100.0, "default_rate": 0.0, "avg_savings": avg_savings}
        
        # Calculate collection rate
        total_disbursed = sum(float(loan.total_amount) for loan in group_loans)
        total_collected = sum(float(loan.amount_paid) for loan in group_loans)
        collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 100.0
        
        # Calculate default rate
        defaulted_loans = len([loan for loan in group_loans if loan.status == 'defaulted'])
        default_rate = (defaulted_loans / len(group_loans) * 100) if group_loans else 0.0
        
        # Calculate average savings
        savings_accounts = db.query(SavingsAccount).filter(
            SavingsAccount.user_id.in_(member_ids)
        ).all()
        avg_savings = np.mean([float(acc.balance) for acc in savings_accounts]) if savings_accounts else 0.0
        
        return {
            "collection_rate": collection_rate,
            "default_rate": default_rate,
            "avg_savings": avg_savings
        }
    
    def _get_risk_category(self, score: float) -> str:
        """Get risk category based on score"""
        if score >= 80:
            return "Low Risk"
        elif score >= 60:
            return "Medium Risk"
        elif score >= 40:
            return "High Risk"
        else:
            return "Very High Risk"
    
    def _get_risk_recommendations(self, score: float, features: Dict) -> List[str]:
        """Generate risk improvement recommendations"""
        recommendations = []
        
        if features.get('payment_punctuality', 1.0) < 0.8:
            recommendations.append("Improve payment punctuality to build credit history")
        
        if features.get('current_savings', 0) < 2000:
            recommendations.append("Increase savings to improve loan limit and risk profile")
        
        if not features.get('registration_fee_paid', False):
            recommendations.append("Complete registration fee payment to activate full account benefits")
        
        if features.get('loan_utilization_rate', 0) > 0.8:
            recommendations.append("Reduce loan utilization ratio by paying down existing loans")
        
        if features.get('group_default_rate', 0) > 10:
            recommendations.append("Consider group transfer - current group has high default rate")
        
        if len(recommendations) == 0:
            recommendations.append("Excellent risk profile! Continue current financial behavior.")
        
        return recommendations
    
    def predict_default_probability(self, user_id: int) -> Dict[str, Any]:
        """Predict probability of loan default"""
        risk_data = self.calculate_risk_score(user_id)
        
        if "error" in risk_data:
            return risk_data
        
        risk_score = risk_data["risk_score"]
        
        # Convert risk score to default probability
        # Higher risk score = lower default probability
        default_probability = max(0, min(1, (100 - risk_score) / 100))
        
        return {
            "user_id": user_id,
            "default_probability": round(default_probability, 3),
            "confidence_level": "High" if len(risk_data["factors"]) >= 4 else "Medium",
            "risk_category": risk_data["risk_category"],
            "key_factors": self._identify_key_risk_factors(risk_data["factors"])
        }
    
    def _identify_key_risk_factors(self, factors: Dict) -> List[Dict[str, Any]]:
        """Identify key factors contributing to risk"""
        factor_impacts = []
        
        for factor_name, factor_data in factors.items():
            if isinstance(factor_data, dict) and 'score' in factor_data:
                impact_level = "High" if factor_data['contribution'] >= 15 else "Medium" if factor_data['contribution'] >= 10 else "Low"
                
                factor_impacts.append({
                    "factor": factor_name.replace('_', ' ').title(),
                    "score": factor_data['score'],
                    "contribution": factor_data['contribution'],
                    "impact_level": impact_level
                })
        
        # Sort by contribution (highest impact first)
        factor_impacts.sort(key=lambda x: x['contribution'], reverse=True)
        
        return factor_impacts[:5]  # Top 5 factors
    
    def batch_calculate_risk_scores(self, user_ids: List[int]) -> List[Dict[str, Any]]:
        """Calculate risk scores for multiple users"""
        results = []
        
        for user_id in user_ids:
            try:
                risk_data = self.calculate_risk_score(user_id)
                results.append(risk_data)
            except Exception as e:
                results.append({"user_id": user_id, "error": str(e)})
        
        return results


# Initialize risk scoring engine
risk_engine = RiskScoringEngine()