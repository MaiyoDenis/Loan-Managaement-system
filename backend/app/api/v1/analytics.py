"""
Advanced Dashboard Analytics API - The Analytics Command Center
This API provides all the data for beautiful dashboards with AI insights
"""

import os
from typing import List, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, date, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd

from app.database import get_db
from app.models.loan import (
    Loan, Payment, SavingsAccount, DrawdownAccount, 
    BranchInventory, Arrear, LoanProduct, LoanApplication
)
from app.models.user import User
from app.models.branch import Branch, Group, GroupMembership
from app.core.permissions import UserRole
from app.services.analytics import analytics_engine
from app.services.reporting import reporting_engine
from app.schemas.analytics import (
    DashboardStatsResponse,
    BranchAnalyticsResponse,
    CustomerRiskResponse,
    PerformanceLeaderboardResponse,
    ForecastResponse
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    require_admin
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    branch_id: Optional[int] = Query(None),
    days_back: int = Query(30, ge=1, le=365)
) -> Any:
    """
    Get comprehensive dashboard statistics
    🎯 THE MAIN DASHBOARD API - Powers the entire frontend dashboard!
    """
    
    # Determine scope based on user role and branch_id
    if current_user.role == UserRole.CUSTOMER:
        # Customer sees only their own data
        return get_customer_dashboard_stats(db, current_user.id, days_back)
    
    elif current_user.role == UserRole.LOAN_OFFICER:
        # Loan officer sees their groups' data
        return get_loan_officer_dashboard_stats(db, current_user.id, days_back)
    
    elif current_user.role in [UserRole.BRANCH_MANAGER, UserRole.PROCUREMENT_OFFICER]:
        # Branch staff see branch data
        target_branch_id = branch_id or current_user.branch_id
        return get_branch_dashboard_stats(db, target_branch_id, days_back)
    
    else:  # ADMIN
        # Admin sees organization-wide data or specific branch
        return get_admin_dashboard_stats(db, branch_id, days_back)


def get_admin_dashboard_stats(db: Session, branch_id: Optional[int], days_back: int) -> Dict[str, Any]:
    """🏛️ ADMIN SUPREME DASHBOARD - See everything, control everything!"""
    
    # Time range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Base queries
    customer_query = db.query(User).filter(User.role == UserRole.CUSTOMER)
    loan_query = db.query(Loan)
    payment_query = db.query(Payment).filter(Payment.status == "confirmed")
    
    # Apply branch filter if specified
    if branch_id:
        branch_customers = customer_query.filter(User.branch_id == branch_id).all()
        customer_ids = [c.id for c in branch_customers]
        loan_query = loan_query.filter(Loan.borrower_id.in_(customer_ids))
        payment_query = payment_query.join(Loan).filter(Loan.borrower_id.in_(customer_ids))
    
    # Apply date filters
    period_loans = loan_query.filter(Loan.created_at.between(start_date, end_date)).all()
    period_payments = payment_query.filter(Payment.payment_date.between(start_date, end_date)).all()
    
    # 💰 FINANCIAL OVERVIEW
    total_customers = customer_query.count()
    total_branches = db.query(Branch).filter(Branch.is_active == True).count()
    
    # Loan metrics
    total_loans_disbursed = len(period_loans)
    total_amount_disbursed = sum(float(loan.total_amount) for loan in period_loans)
    
    active_loans = loan_query.filter(Loan.status == "active").all()
    completed_loans = loan_query.filter(Loan.status == "completed").all()
    arrears_loans = loan_query.filter(Loan.status == "arrears").all()
    
    outstanding_balance = sum(float(loan.balance) for loan in active_loans + arrears_loans)
    arrears_amount = sum(float(loan.balance) for loan in arrears_loans)
    
    # Payment metrics
    total_payments = len(period_payments)
    total_collected = sum(float(payment.amount) for payment in period_payments)
    collection_rate = (total_collected / total_amount_disbursed * 100) if total_amount_disbursed > 0 else 0
    
    # 📊 GROWTH METRICS
    previous_start = start_date - timedelta(days=days_back)
    previous_loans = loan_query.filter(Loan.created_at.between(previous_start, start_date)).all()
    previous_amount = sum(float(loan.total_amount) for loan in previous_loans)
    
    growth_rate = ((total_amount_disbursed - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0
    
    # 🎯 TOP PERFORMERS
    branch_rankings = analytics_engine.get_branch_performance_ranking()
    top_branches = branch_rankings[:5]  # Top 5 branches
    
    officer_rankings = analytics_engine.get_loan_officer_performance(branch_id)
    top_officers = officer_rankings[:5]  # Top 5 officers
    
    # 🚨 RISK ALERTS
    arrears_forecast = analytics_engine.forecast_arrears_risk(7, branch_id)  # Next 7 days
    high_risk_loans = arrears_forecast.get("risk_categories", {}).get("high_risk", {}).get("loans", [])
    
    # 📈 INVENTORY ALERTS
    inventory_query = db.query(BranchInventory).join(LoanProduct)
    if branch_id:
        inventory_query = inventory_query.filter(BranchInventory.branch_id == branch_id)
    
    inventory_items = inventory_query.all()
    low_stock_items = [item for item in inventory_items if item.status in ["low", "critical"]]
    
    # 💎 PROFIT ANALYSIS (Admin Only Secret Data)
    total_inventory_value = sum(
        float(item.loan_product.buying_price) * item.current_quantity
        for item in inventory_items
    )
    
    total_potential_sales = sum(
        float(item.loan_product.selling_price) * item.current_quantity
        for item in inventory_items
    )
    
    potential_profit = total_potential_sales - total_inventory_value
    profit_margin = (potential_profit / total_inventory_value * 100) if total_inventory_value > 0 else 0
    
    # 📱 DAILY TRENDS (Last 30 days)
    daily_trends = []
    for i in range(30):
        trend_date = end_date - timedelta(days=i)
        
        daily_loans = [loan for loan in period_loans if loan.created_at.date() == trend_date]
        daily_payments = [payment for payment in period_payments if payment.payment_date == trend_date]
        
        daily_trends.append({
            "date": trend_date.isoformat(),
            "loans_count": len(daily_loans),
            "loans_amount": sum(float(loan.total_amount) for loan in daily_loans),
            "payments_count": len(daily_payments),
            "payments_amount": sum(float(payment.amount) for payment in daily_payments)
        })
    
    daily_trends.reverse()  # Oldest to newest
    
    return {
        # 🏦 ORGANIZATION OVERVIEW
        "organization_overview": {
            "total_customers": total_customers,
            "total_branches": total_branches,
            "total_loan_officers": db.query(User).filter(User.role == UserRole.LOAN_OFFICER).count(),
            "total_groups": db.query(Group).filter(Group.is_active == True).count()
        },
        
        # 💰 FINANCIAL SUMMARY
        "financial_summary": {
            "total_loans_disbursed": total_loans_disbursed,
            "total_amount_disbursed": total_amount_disbursed,
            "total_payments": total_payments,
            "total_collected": total_collected,
            "outstanding_balance": outstanding_balance,
            "arrears_amount": arrears_amount,
            "collection_rate": round(collection_rate, 2),
            "arrears_rate": round((arrears_amount / outstanding_balance * 100) if outstanding_balance > 0 else 0, 2),
            "growth_rate": round(growth_rate, 2)
        },
        
        # 📊 LOAN BREAKDOWN
        "loan_breakdown": {
            "active": len(active_loans),
            "completed": len(completed_loans),
            "arrears": len(arrears_loans),
            "total": len(active_loans) + len(completed_loans) + len(arrears_loans)
        },
        
        # 🏆 TOP PERFORMERS
        "top_performers": {
            "branches": top_branches,
            "loan_officers": top_officers
        },
        
        # 🚨 ALERTS & RISKS
        "alerts": {
            "high_risk_loans": len(high_risk_loans),
            "high_risk_amount": sum(loan["balance"] for loan in high_risk_loans),
            "low_stock_items": len(low_stock_items),
            "critical_stock_items": len([item for item in low_stock_items if item.status == "critical"]),
            "pending_approvals": db.query(Payment).filter(Payment.status == "pending").count()
        },
        
        # 💎 PROFIT INSIGHTS (Admin Secret Data)
        "profit_insights": {
            "total_inventory_value": total_inventory_value,
            "potential_sales_value": total_potential_sales,
            "potential_profit": potential_profit,
            "profit_margin": round(profit_margin, 2),
            "total_products": len(inventory_items)
        },
        
        # 📈 TRENDS
        "trends": {
            "daily_data": daily_trends,
            "period_days": days_back,
            "growth_rate": round(growth_rate, 2)
        },
        
        # 🎯 QUICK ACTIONS
        "quick_actions": {
            "loans_due_today": db.query(Loan).filter(
                Loan.next_payment_date == date.today(),
                Loan.status == "active"
            ).count(),
            "applications_pending": db.query(LoanApplication).filter(
                LoanApplication.status.in_(["submitted", "pending", "under_review"])
            ).count(),
            "customers_online": db.query(User).filter(User.is_online == True).count()
        },
        
        "generated_at": datetime.utcnow().isoformat(),
        "scope": "Organization-wide" if not branch_id else f"Branch {branch_id}",
        "user_role": "admin"
    }


def get_branch_dashboard_stats(db: Session, branch_id: int, days_back: int) -> Dict[str, Any]:
    """🏢 BRANCH MANAGER DASHBOARD - Complete branch oversight"""
    
    # Get branch
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    # Time range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Get branch customers
    branch_customers = db.query(User).filter(
        User.branch_id == branch_id,
        User.role == UserRole.CUSTOMER
    ).all()
    customer_ids = [c.id for c in branch_customers]
    
    # Branch KPIs
    branch_kpis = analytics_engine._calculate_branch_kpis(branch_id)
    
    # Loan officer performance in this branch
    officer_performance = analytics_engine.get_loan_officer_performance(branch_id)
    
    # Group performance
    branch_groups = db.query(Group).filter(Group.branch_id == branch_id).all()
    group_performance = []
    
    for group in branch_groups:
        group_members = db.query(GroupMembership).filter(
            GroupMembership.group_id == group.id,
            GroupMembership.is_active == True
        ).all()
        member_ids = [gm.member_id for gm in group_members]
        
        group_loans = db.query(Loan).filter(Loan.borrower_id.in_(member_ids)).all()
        group_savings = db.query(SavingsAccount).filter(SavingsAccount.user_id.in_(member_ids)).all()
        
        total_savings = sum(float(acc.balance) for acc in group_savings)
        total_loans = sum(float(loan.total_amount) for loan in group_loans)
        active_loans = len([loan for loan in group_loans if loan.status == "active"])
        
        group_performance.append({
            "group_id": group.id,
            "group_name": group.name,
            "loan_officer": f"{group.loan_officer.first_name} {group.loan_officer.last_name}",
            "total_members": len(group_members),
            "total_savings": total_savings,
            "total_loans": total_loans,
            "active_loans": active_loans,
            "avg_savings_per_member": total_savings / len(group_members) if group_members else 0,
            "performance_score": (total_savings / 1000 + active_loans * 10) if group_members else 0
        })
    
    # Sort groups by performance
    group_performance.sort(key=lambda x: x["performance_score"], reverse=True)
    
    # Inventory status
    branch_inventory = db.query(BranchInventory).filter(
        BranchInventory.branch_id == branch_id
    ).all()
    
    inventory_alerts = []
    for item in branch_inventory:
        if item.status in ["low", "critical"]:
            inventory_alerts.append({
                "product_name": item.loan_product.name,
                "current_quantity": item.current_quantity,
                "reorder_point": item.reorder_point,
                "status": item.status,
                "alert_level": "high" if item.status == "critical" else "medium"
            })
    
    # Recent activities (last 7 days)
    recent_activities = []
    
    # Recent loans
    recent_loans = db.query(Loan).filter(
        Loan.borrower_id.in_(customer_ids),
        Loan.created_at >= datetime.utcnow() - timedelta(days=7)
    ).all()
    
    for loan in recent_loans:
        recent_activities.append({
            "type": "loan_disbursed",
            "description": f"Loan {loan.loan_number} disbursed to {loan.borrower.first_name} {loan.borrower.last_name}",
            "amount": float(loan.total_amount),
            "timestamp": loan.created_at.isoformat(),
            "user": f"{loan.borrower.first_name} {loan.borrower.last_name}"
        })
    
    # Recent payments
    recent_payments = db.query(Payment).join(Loan).filter(
        Loan.borrower_id.in_(customer_ids),
        Payment.payment_date >= date.today() - timedelta(days=7),
        Payment.status == "confirmed"
    ).all()
    
    for payment in recent_payments:
        recent_activities.append({
            "type": "payment_received",
            "description": f"Payment of KES {payment.amount} received for loan {payment.loan.loan_number}",
            "amount": float(payment.amount),
            "timestamp": payment.created_at.isoformat(),
            "user": f"{payment.payer.first_name} {payment.payer.last_name}"
        })
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {
        "dashboard_type": "branch_manager",
        "branch_info": {
            "branch_id": branch_id,
            "branch_name": branch.name,
            "branch_code": branch.code,
            "manager_name": f"{branch.manager.first_name} {branch.manager.last_name}" if branch.manager else "No Manager"
        },
        "kpis": branch_kpis,
        "performance_insights": {
            "loan_officers": officer_performance,
            "groups": group_performance[:10],  # Top 10 groups
            "branch_rank": next((i+1 for i, b in enumerate(analytics_engine.get_branch_performance_ranking()) if b["branch_id"] == branch_id), 0)
        },
        "inventory_status": {
            "total_products": len(branch_inventory),
            "low_stock_alerts": len(inventory_alerts),
            "alerts": inventory_alerts
        },
        "recent_activities": recent_activities[:20],  # Last 20 activities
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "generated_at": datetime.utcnow().isoformat()
    }


def get_loan_officer_dashboard_stats(db: Session, loan_officer_id: int, days_back: int) -> Dict[str, Any]:
    """👥 LOAN OFFICER DASHBOARD - Manage your groups like a pro!"""
    
    # Get loan officer's groups
    officer_groups = db.query(Group).filter(
        Group.loan_officer_id == loan_officer_id,
        Group.is_active == True
    ).all()
    
    if not officer_groups:
        return {
            "dashboard_type": "loan_officer",
            "message": "No groups assigned",
            "groups": [],
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # Get all group members
    group_ids = [g.id for g in officer_groups]
    group_memberships = db.query(GroupMembership).filter(
        GroupMembership.group_id.in_(group_ids),
        GroupMembership.is_active == True
    ).all()
    member_ids = [gm.member_id for gm in group_memberships]
    
    # Time range
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    # Loans and payments for officer's customers
    officer_loans = db.query(Loan).filter(Loan.borrower_id.in_(member_ids)).all()
    period_loans = [loan for loan in officer_loans if start_date <= loan.created_at.date() <= end_date]
    
    officer_payments = db.query(Payment).join(Loan).filter(
        Loan.borrower_id.in_(member_ids),
        Payment.payment_date.between(start_date, end_date),
        Payment.status == "confirmed"
    ).all()
    
    # Calculate officer performance metrics
    total_customers = len(member_ids)
    active_loans = [loan for loan in officer_loans if loan.status == "active"]
    completed_loans = [loan for loan in officer_loans if loan.status == "completed"]
    arrears_loans = [loan for loan in officer_loans if loan.status == "arrears"]
    
    total_disbursed = sum(float(loan.total_amount) for loan in period_loans)
    total_collected = sum(float(payment.amount) for payment in officer_payments)
    collection_rate = (total_collected / total_disbursed * 100) if total_disbursed > 0 else 0
    
    # Group performance breakdown
    group_details = []
    for group in officer_groups:
        group_members = [gm for gm in group_memberships if gm.group_id == group.id]
        group_member_ids = [gm.member_id for gm in group_members]
        
        group_loans = [loan for loan in officer_loans if loan.borrower_id in group_member_ids]
        group_savings = db.query(SavingsAccount).filter(
            SavingsAccount.user_id.in_(group_member_ids)
        ).all()
        
        group_total_savings = sum(float(acc.balance) for acc in group_savings)
        group_active_loans = len([loan for loan in group_loans if loan.status == "active"])
        group_arrears = len([loan for loan in group_loans if loan.status == "arrears"])
        
        # Calculate group risk score
        group_risk_scores = []
        for member_id in group_member_ids:
            risk_data = analytics_engine.calculate_customer_risk_score(member_id)
            if "risk_score" in risk_data:
                group_risk_scores.append(risk_data["risk_score"])
        
        avg_group_risk = np.mean(group_risk_scores) if group_risk_scores else 50
        
        group_details.append({
            "group_id": group.id,
            "group_name": group.name,
            "total_members": len(group_members),
            "total_savings": group_total_savings,
            "active_loans": group_active_loans,
            "arrears_loans": group_arrears,
            "avg_risk_score": round(avg_group_risk, 2),
            "performance_grade": analytics_engine._get_performance_grade(avg_group_risk),
            "next_due_payments": db.query(Loan).filter(
                Loan.borrower_id.in_(group_member_ids),
                Loan.next_payment_date.between(date.today(), date.today() + timedelta(days=7)),
                Loan.status == "active"
            ).count()
        })
    
    # Upcoming tasks and alerts
    upcoming_tasks = []
    
    # Loans due in next 7 days
    upcoming_due = db.query(Loan).filter(
        Loan.borrower_id.in_(member_ids),
        Loan.next_payment_date.between(date.today(), date.today() + timedelta(days=7)),
        Loan.status == "active"
    ).all()
    
    for loan in upcoming_due:
        days_remaining = (loan.next_payment_date - date.today()).days
        upcoming_tasks.append({
            "type": "payment_due",
            "priority": "high" if days_remaining <= 1 else "medium",
            "description": f"Payment due for {loan.borrower.first_name} {loan.borrower.last_name} - Loan {loan.loan_number}",
            "amount": float(loan.next_payment_amount or loan.balance),
            "due_date": loan.next_payment_date.isoformat(),
            "days_remaining": days_remaining,
            "customer_phone": loan.borrower.phone_number
        })
    
    # Customers with low savings
    low_savings_customers = db.query(SavingsAccount).filter(
        SavingsAccount.user_id.in_(member_ids),
        SavingsAccount.balance < 1000  # Less than 1000
    ).all()
    
    for acc in low_savings_customers:
        upcoming_tasks.append({
            "type": "low_savings",
            "priority": "low",
            "description": f"Encourage {acc.user.first_name} {acc.user.last_name} to increase savings",
            "amount": float(acc.balance),
            "recommendation": "Target savings increase to improve loan capacity"
        })
    
    return {
        "dashboard_type": "loan_officer",
        "officer_info": {
            "total_groups": len(officer_groups),
            "total_customers": total_customers,
            "performance_rank": next(
                (i+1 for i, officer in enumerate(analytics_engine.get_loan_officer_performance()) 
                 if officer["officer_id"] == loan_officer_id), 0
            )
        },
        "performance_metrics": {
            "collection_rate": round(collection_rate, 2),
            "total_loans": len(officer_loans),
            "active_loans": len(active_loans),
            "completed_loans": len(completed_loans),
            "arrears_loans": len(arrears_loans),
            "total_portfolio": sum(float(loan.balance) for loan in active_loans + arrears_loans)
        },
        "groups": group_details,
        "upcoming_tasks": sorted(upcoming_tasks, key=lambda x: x.get("days_remaining", 999)),
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "generated_at": datetime.utcnow().isoformat()
    }


def get_customer_dashboard_stats(db: Session, customer_id: int, days_back: int) -> Dict[str, Any]:
    """👤 CUSTOMER DASHBOARD - Personal financial overview"""
    
    customer = db.query(User).filter(User.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Get customer's accounts
    savings_account = customer.savings_account
    drawdown_account = customer.drawdown_account
    
    # Get customer's loans
    customer_loans = db.query(Loan).filter(Loan.borrower_id == customer_id).all()
    active_loans = [loan for loan in customer_loans if loan.status == "active"]
    
    # Get recent transactions
    from app.models.loan import Transaction
    recent_transactions = db.query(Transaction).filter(
        Transaction.user_id == customer_id
    ).order_by(Transaction.created_at.desc()).limit(10).all()
    
    # Get available loan products
    if customer.branch_id:
        available_products = db.query(LoanProduct).join(BranchInventory).filter(
            BranchInventory.branch_id == customer.branch_id,
            BranchInventory.current_quantity > 0,
            LoanProduct.is_active == True
        ).all()
    else:
        available_products = []
    
    # Calculate loan eligibility
    if savings_account:
        loan_limit = float(savings_account.loan_limit)
        current_loan_balance = sum(float(loan.balance) for loan in active_loans)
        available_loan_capacity = loan_limit - current_loan_balance
    else:
        loan_limit = 0
        available_loan_capacity = 0
    
    # Payment schedule for next 30 days
    payment_schedule = []
    for loan in active_loans:
        if loan.next_payment_date and loan.next_payment_date <= date.today() + timedelta(days=30):
            payment_schedule.append({
                "loan_number": loan.loan_number,
                "due_date": loan.next_payment_date.isoformat(),
                "amount": float(loan.next_payment_amount or loan.balance),
                "days_remaining": (loan.next_payment_date - date.today()).days,
                "can_auto_pay": float(drawdown_account.balance) >= float(loan.next_payment_amount or loan.balance) if drawdown_account else False
            })
    
    payment_schedule.sort(key=lambda x: x["days_remaining"])
    
    return {
        "dashboard_type": "customer",
        "customer_info": {
            "name": f"{customer.first_name} {customer.last_name}",
            "account_number": customer.unique_account_number,
            "registration_status": savings_account.status if savings_account else "pending",
            "member_since": customer.created_at.strftime("%B %Y")
        },
        "account_summary": {
            "savings_balance": float(savings_account.balance) if savings_account else 0,
            "drawdown_balance": float(drawdown_account.balance) if drawdown_account else 0,
            "loan_limit": loan_limit,
            "available_capacity": max(0, available_loan_capacity),
            "registration_fee_paid": savings_account.registration_fee_paid if savings_account else False
        },
        "loan_overview": {
            "total_loans": len(customer_loans),
            "active_loans": len(active_loans),
            "completed_loans": len([loan for loan in customer_loans if loan.status == "completed"]),
            "total_borrowed": sum(float(loan.total_amount) for loan in customer_loans),
            "total_outstanding": sum(float(loan.balance) for loan in active_loans),
            "next_payment": payment_schedule[0] if payment_schedule else None
        },
        "available_products": [
            {
                "product_id": product.id,
                "product_name": product.name,
                "category": product.category.name,
                "price": float(product.selling_price),
                "description": product.description
            }
            for product in available_products[:10]  # Show top 10 available products
        ],
        "payment_schedule": payment_schedule,
        "recent_transactions": [
            {
                "transaction_number": tx.transaction_number,
                "type": tx.transaction_type,
                "account": tx.account_type,
                "amount": float(tx.amount),
                "balance_after": float(tx.balance_after),
                "date": tx.created_at.strftime("%Y-%m-%d %H:%M"),
                "description": tx.description
            }
            for tx in recent_transactions
        ],
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/risk-analysis/{customer_id}", response_model=CustomerRiskResponse)
def get_customer_risk_analysis(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """🎯 AI-POWERED CUSTOMER RISK ANALYSIS"""
    
    # Check access permissions
    if current_user.role == UserRole.CUSTOMER:
        if current_user.id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    elif current_user.role != UserRole.ADMIN:
        customer = db.query(User).filter(User.id == customer_id).first()
        if not customer or customer.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get comprehensive risk analysis
    risk_analysis = analytics_engine.calculate_customer_risk_score(customer_id)
    
    if "error" in risk_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=risk_analysis["error"]
        )
    
    return risk_analysis


@router.get("/leaderboard", response_model=PerformanceLeaderboardResponse)
def get_performance_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    leaderboard_type: str = Query("branches", regex="^(branches|officers|groups|customers)$"),
    branch_id: Optional[int] = Query(None),
    limit: int = Query(10, ge=5, le=50)
) -> Any:
    """🏆 PERFORMANCE LEADERBOARDS - See who's winning!"""
    
    if leaderboard_type == "branches":
        # Branch performance leaderboard
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can view branch leaderboard"
            )
        
        rankings = analytics_engine.get_branch_performance_ranking()[:limit]
        
        return {
            "leaderboard_type": "branches",
            "title": "Top Performing Branches",
            "rankings": rankings,
            "total_entries": len(rankings),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    elif leaderboard_type == "officers":
        # Loan officer performance leaderboard
        rankings = analytics_engine.get_loan_officer_performance(branch_id)[:limit]
        
        return {
            "leaderboard_type": "loan_officers",
            "title": f"Top Performing Loan Officers{' - ' + db.query(Branch).filter(Branch.id == branch_id).first().name if branch_id else ''}",
            "rankings": rankings,
            "total_entries": len(rankings),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    else:
        return {"error": "Leaderboard type not implemented yet"}


@router.get("/forecast/arrears", response_model=ForecastResponse)
def get_arrears_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days_ahead: int = Query(30, ge=7, le=365),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """🔮 PREDICTIVE ARREARS FORECASTING - See the future!"""
    
    # Check branch access
    if current_user.role not in [UserRole.ADMIN, UserRole.BRANCH_MANAGER, UserRole.PROCUREMENT_OFFICER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to forecasting data"
        )
    
    if current_user.role != UserRole.ADMIN:
        branch_id = current_user.branch_id
    
    # Generate forecast
    forecast = analytics_engine.forecast_arrears_risk(days_ahead, branch_id)
    
    if "error" in forecast:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=forecast["error"]
        )
    
    return forecast


@router.post("/generate-report")
async def generate_custom_report(
    background_tasks: BackgroundTasks,
    report_type: str,
    format: str = "pdf",
    branch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:export"))
) -> Any:
    """📊 GENERATE CUSTOM REPORTS - Beautiful PDFs and Excel files"""
    
    # Add report generation to background tasks
    background_tasks.add_task(
        generate_report_background,
        report_type=report_type,
        format=format,
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        user_id=current_user.id
    )
    
    return {
        "message": "Report generation started",
        "report_type": report_type,
        "format": format,
        "estimated_completion": "2-5 minutes",
        "notification": "You will be notified when the report is ready"
    }


async def generate_report_background(report_type: str, format: str, branch_id: Optional[int],
                                   start_date: Optional[date], end_date: Optional[date], 
                                   user_id: int):
    """Background task for report generation"""
    try:
        if report_type == "branch_performance":
            if not branch_id:
                raise ValueError("Branch ID required for branch performance report")
            
            result = reporting_engine.generate_branch_performance_report(
                branch_id=branch_id,
                start_date=start_date or (date.today() - timedelta(days=30)),
                end_date=end_date or date.today(),
                format=format
            )
        
        elif report_type == "financial_summary":
            result = reporting_engine.generate_financial_summary_report(
                branch_id=branch_id,
                start_date=start_date,
                end_date=end_date,
                format=format
            )
        
        elif report_type == "risk_assessment":
            result = reporting_engine.generate_risk_assessment_report(
                branch_id=branch_id,
                format=format
            )
        
        else:
            result = {"error": "Unknown report type"}
        
        # Notify user when report is ready
        if result.get("success"):
            from app.services.notification import notification_service
            await notification_service.send_notification(
                recipient_id=user_id,
                title="Report Ready for Download",
                message=f"Your {report_type} report has been generated successfully. File: {result['file_path']}",
                notification_type="report_ready"
            )
        else:
            await notification_service.send_notification(
                recipient_id=user_id,
                title="Report Generation Failed",
                message=f"Failed to generate {report_type} report. Error: {result.get('error', 'Unknown error')}",
                notification_type="error"
            )
    
    except Exception as e:
        # Notify user of failure
        from app.services.notification import notification_service
        await notification_service.send_notification(
            recipient_id=user_id,
            title="Report Generation Error",
            message=f"Error generating report: {str(e)}",
            notification_type="error"
        )


@router.get("/export/excel/{report_type}")
def export_data_to_excel(
    report_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("reports:export")),
    branch_id: Optional[int] = Query(None)
) -> Any:
    """📋 QUICK EXCEL EXPORT - Download data instantly"""
    
    try:
        if report_type == "customers":
            # Export customer data
            query = db.query(User).filter(User.role == UserRole.CUSTOMER)
            
            if current_user.role != UserRole.ADMIN:
                query = query.filter(User.branch_id == current_user.branch_id)
            elif branch_id:
                query = query.filter(User.branch_id == branch_id)
            
            customers = query.all()
            
            filename = f"customers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            file_path = os.path.join(reporting_engine.reports_dir, filename)
            
            # Create Excel file
            customer_data = []
            for customer in customers:
                savings = customer.savings_account
                active_loans_count = len([loan for loan in customer.loans if loan.status == "active"])
                
                customer_data.append({
                    "Customer ID": customer.id,
                    "Name": f"{customer.first_name} {customer.last_name}",
                    "Phone": customer.phone_number,
                    "Account Number": customer.unique_account_number,
                    "Savings Balance": float(savings.balance) if savings else 0,
                    "Loan Limit": float(savings.loan_limit) if savings else 0,
                    "Active Loans": active_loans_count,
                    "Registration Status": savings.status if savings else "pending",
                    "Member Since": customer.created_at.strftime("%Y-%m-%d")
                })
            
            df = pd.DataFrame(customer_data)
            df.to_excel(file_path, index=False)
            
            return {
                "success": True,
                "file_path": file_path,
                "filename": filename,
                "records_exported": len(customer_data)
            }
        
        else:
            return {"error": "Unsupported export type"}
    
    except Exception as e:
        return {"error": str(e)}