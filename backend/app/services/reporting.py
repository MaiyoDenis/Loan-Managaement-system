"""
Advanced Reporting Engine with PDF and Excel Export
"""

import pandas as pd
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.permissions import UserRole
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
import os

from app.database import SessionLocal
from app.models.loan import Loan, Payment, SavingsAccount, LoanProduct, BranchInventory
from app.models.user import User
from app.models.branch import Branch, Group
from app.services.analytics import analytics_engine


class ReportingEngine:
    """Advanced reporting engine with export capabilities"""
    
    def __init__(self):
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Initialize chart styling
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def generate_branch_performance_report(self, branch_id: int, 
                                         start_date: date, end_date: date,
                                         format: str = "pdf") -> Dict[str, Any]:
        """Generate comprehensive branch performance report"""
        db = SessionLocal()
        try:
            # Get branch information
            branch = db.query(Branch).filter(Branch.id == branch_id).first()
            if not branch:
                return {"error": "Branch not found"}
            
            # Collect data
            report_data = {
                "branch_info": {
                    "name": branch.name,
                    "code": branch.code,
                    "manager": f"{branch.manager.first_name} {branch.manager.last_name}" if branch.manager else "Not Assigned",
                    "procurement_officer": f"{branch.procurement_officer.first_name} {branch.procurement_officer.last_name}" if branch.procurement_officer else "Not Assigned",
                    "report_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            # Financial metrics
            financial_data = self._get_branch_financial_data(db, branch_id, start_date, end_date)
            report_data["financial_metrics"] = financial_data
            
            # Customer analytics
            customer_data = self._get_branch_customer_analytics(db, branch_id, start_date, end_date)
            report_data["customer_analytics"] = customer_data
            
            # Loan portfolio analysis
            portfolio_data = self._get_portfolio_analysis(db, branch_id, start_date, end_date)
            report_data["portfolio_analysis"] = portfolio_data
            
            # Risk assessment
            risk_data = self._get_risk_assessment(db, branch_id)
            report_data["risk_assessment"] = risk_data
            
            # Staff performance
            staff_data = self._get_staff_performance(db, branch_id, start_date, end_date)
            report_data["staff_performance"] = staff_data
            
            # Generate charts
            charts = self._generate_report_charts(report_data)
            report_data["charts"] = charts
            
            # Export based on format
            if format.lower() == "pdf":
                file_path = self._export_to_pdf(report_data)
            elif format.lower() == "excel":
                file_path = self._export_to_excel(report_data)
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "report_data": report_data,
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()
    
    def _get_branch_financial_data(self, db: Session, branch_id: int, 
                                  start_date: date, end_date: date) -> Dict[str, Any]:
        """Get comprehensive branch financial data"""
        
        # Get branch customers
        branch_customers = db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        customer_ids = [c.id for c in branch_customers]
        
        # Loans analysis
        period_loans = db.query(Loan).filter(
            Loan.borrower_id.in_(customer_ids),
            Loan.start_date >= start_date,
            Loan.start_date <= end_date
        ).all()
        
        all_branch_loans = db.query(Loan).filter(
            Loan.borrower_id.in_(customer_ids)
        ).all()
        
        # Payments analysis
        period_payments = db.query(Payment).join(Loan).filter(
            Loan.borrower_id.in_(customer_ids),
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date,
            Payment.status == 'confirmed'
        ).all()
        
        # Calculate metrics
        loans_disbursed = len(period_loans)
        amount_disbursed = sum(float(loan.total_amount) for loan in period_loans)
        
        payments_received = len(period_payments)
        amount_collected = sum(float(payment.amount) for payment in period_payments)
        
        # Outstanding portfolio
        active_loans = [loan for loan in all_branch_loans if loan.status in ['active', 'arrears']]
        total_outstanding = sum(float(loan.balance) for loan in active_loans)
        
        # Savings analysis
        savings_accounts = db.query(SavingsAccount).join(User).filter(
            User.id.in_(customer_ids)
        ).all()
        
        total_savings = sum(float(acc.balance) for acc in savings_accounts)
        active_customers = len([acc for acc in savings_accounts if acc.registration_fee_paid])
        
        # Collection efficiency
        collection_rate = (amount_collected / amount_disbursed * 100) if amount_disbursed > 0 else 0
        
        return {
            "period_summary": {
                "loans_disbursed": loans_disbursed,
                "amount_disbursed": amount_disbursed,
                "payments_received": payments_received,
                "amount_collected": amount_collected,
                "collection_rate": round(collection_rate, 2)
            },
            "portfolio_status": {
                "total_outstanding": total_outstanding,
                "active_loans": len(active_loans),
                "total_customers": len(branch_customers),
                "active_customers": active_customers,
                "total_savings": total_savings
            },
            "profitability": {
                "interest_income": sum(float(loan.interest_amount) for loan in period_loans),
                "charge_fee_income": sum(float(loan.charge_fee_amount) for loan in period_loans),
                "gross_margin": sum(float(loan.interest_amount + loan.charge_fee_amount) for loan in period_loans)
            }
        }
    
    def _get_branch_customer_analytics(self, db: Session, branch_id: int,
                                     start_date: date, end_date: date) -> Dict[str, Any]:
        """Get customer analytics for branch"""
        
        branch_customers = db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        
        # Customer segmentation
        segments = {
            "new_customers": [],
            "active_customers": [],
            "dormant_customers": [],
            "high_value_customers": []
        }
        
        for customer in branch_customers:
            # Check if new customer (registered in period)
            if start_date <= customer.created_at.date() <= end_date:
                segments["new_customers"].append(customer)
            
            # Check if active (has recent transactions)
            recent_activity = db.query(Payment).join(Loan).filter(
                Loan.borrower_id == customer.id,
                Payment.payment_date >= end_date - timedelta(days=30),
                Payment.status == 'confirmed'
            ).first()
            
            if recent_activity:
                segments["active_customers"].append(customer)
            else:
                segments["dormant_customers"].append(customer)
            
            # Check if high value (savings > 10,000)
            if customer.savings_account and customer.savings_account.balance >= 10000:
                segments["high_value_customers"].append(customer)
        
        # Customer behavior analysis
        avg_loan_size = db.query(func.avg(Loan.total_amount)).join(User).filter(
            User.branch_id == branch_id,
            Loan.start_date >= start_date,
            Loan.start_date <= end_date
        ).scalar() or 0
        
        avg_savings_balance = db.query(func.avg(SavingsAccount.balance)).join(User).filter(
            User.branch_id == branch_id
        ).scalar() or 0
        
        return {
            "total_customers": len(branch_customers),
            "customer_segments": {
                "new_customers": len(segments["new_customers"]),
                "active_customers": len(segments["active_customers"]),
                "dormant_customers": len(segments["dormant_customers"]),
                "high_value_customers": len(segments["high_value_customers"])
            },
            "customer_behavior": {
                "avg_loan_size": float(avg_loan_size),
                "avg_savings_balance": float(avg_savings_balance),
                "customer_retention_rate": (len(segments["active_customers"]) / len(branch_customers) * 100) if branch_customers else 0
            }
        }
    
    def _generate_report_charts(self, report_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts for reports"""
        charts = {}
        
        try:
            # Chart 1: Monthly Payment Trends
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Sample data for demonstration
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
            amounts = [50000, 75000, 60000, 85000, 90000, 70000]
            
            ax.plot(months, amounts, marker='o', linewidth=2, markersize=8)
            ax.set_title('Monthly Payment Collections', fontsize=16, fontweight='bold')
            ax.set_xlabel('Month')
            ax.set_ylabel('Amount (KES)')
            ax.grid(True, alpha=0.3)
            
            # Save chart
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
            chart_buffer.seek(0)
            chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode()
            charts["payment_trends"] = chart_base64
            plt.close()
            
            # Chart 2: Risk Distribution Pie Chart
            fig, ax = plt.subplots(figsize=(8, 8))
            
            risk_categories = ['Low Risk', 'Medium Risk', 'High Risk', 'Very High Risk']
            risk_values = [60, 25, 12, 3]
            colors_pie = ['#2E8B57', '#FFD700', '#FF8C00', '#DC143C']
            
            ax.pie(risk_values, labels=risk_categories, autopct='%1.1f%%', 
                  colors=colors_pie, startangle=90)
            ax.set_title('Portfolio Risk Distribution', fontsize=16, fontweight='bold')
            
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
            chart_buffer.seek(0)
            chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode()
            charts["risk_distribution"] = chart_base64
            plt.close()
            
            # Chart 3: Collection Rate Trends
            fig, ax = plt.subplots(figsize=(10, 6))
            
            weeks = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
            collection_rates = [95, 87, 92, 89]
            target_line = [85] * len(weeks)
            
            ax.bar(weeks, collection_rates, alpha=0.7, color='skyblue', label='Actual')
            ax.plot(weeks, target_line, 'r--', linewidth=2, label='Target (85%)')
            ax.set_title('Weekly Collection Rate Performance', fontsize=16, fontweight='bold')
            ax.set_ylabel('Collection Rate (%)')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
            chart_buffer.seek(0)
            chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode()
            charts["collection_trends"] = chart_base64
            plt.close()
            
        except Exception as e:
            print(f"Error generating charts: {e}")
        
        return charts
    
    def _export_to_pdf(self, report_data: Dict[str, Any]) -> str:
        """Export report to PDF format"""
        
        # Create filename
        branch_name = report_data["branch_info"]["name"].replace(" ", "_")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"branch_report_{branch_name}_{timestamp}.pdf"
        file_path = os.path.join(self.reports_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("Kim Loans Management System", title_style))
        story.append(Paragraph("Branch Performance Report", title_style))
        story.append(Spacer(1, 20))
        
        # Branch Information
        branch_info = report_data["branch_info"]
        branch_table_data = [
            ["Branch Name", branch_info["name"]],
            ["Branch Code", branch_info["code"]],
            ["Manager", branch_info["manager"]],
            ["Procurement Officer", branch_info["procurement_officer"]],
            ["Report Period", branch_info["report_period"]],
            ["Generated", branch_info["generated_at"]]
        ]
        
        branch_table = Table(branch_table_data, colWidths=[2*inch, 4*inch])
        branch_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(branch_table)
        story.append(Spacer(1, 30))
        
        # Financial Summary
        story.append(Paragraph("Financial Summary", styles['Heading2']))
        financial_metrics = report_data["financial_metrics"]["period_summary"]
        
        financial_table_data = [
            ["Metric", "Value", "Target", "Status"],
            ["Loans Disbursed", str(financial_metrics["loans_disbursed"]), "N/A", "✓"],
            ["Amount Disbursed", f"KES {financial_metrics['amount_disbursed']:,.2f}", "N/A", "✓"],
            ["Payments Received", str(financial_metrics["payments_received"]), "N/A", "✓"],
            ["Amount Collected", f"KES {financial_metrics['amount_collected']:,.2f}", "N/A", "✓"],
            ["Collection Rate", f"{financial_metrics['collection_rate']:.1f}%", "85%", 
             "✓" if financial_metrics["collection_rate"] >= 85 else "⚠"]
        ]
        
        financial_table = Table(financial_table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 0.8*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10)
        ]))
        
        story.append(financial_table)
        story.append(Spacer(1, 20))
        
        # Add charts if available
        if "charts" in report_data:
            for chart_name, chart_data in report_data["charts"].items():
                if chart_data:
                    try:
                        # Decode base64 chart and add to PDF
                        chart_buffer = BytesIO(base64.b64decode(chart_data))
                        chart_image = Image(chart_buffer, width=6*inch, height=4*inch)
                        story.append(chart_image)
                        story.append(Spacer(1, 20))
                    except Exception as e:
                        print(f"Error adding chart {chart_name}: {e}")
        
        # Build PDF
        doc.build(story)
        
        return file_path
    
    def _export_to_excel(self, report_data: Dict[str, Any]) -> str:
        """Export report to Excel format"""
        
        # Create filename
        branch_name = report_data["branch_info"]["name"].replace(" ", "_")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"branch_report_{branch_name}_{timestamp}.xlsx"
        file_path = os.path.join(self.reports_dir, filename)
        
        # Create Excel writer
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            
            # Branch Information Sheet
            branch_df = pd.DataFrame([
                ["Branch Name", report_data["branch_info"]["name"]],
                ["Branch Code", report_data["branch_info"]["code"]],
                ["Manager", report_data["branch_info"]["manager"]],
                ["Report Period", report_data["branch_info"]["report_period"]],
                ["Generated", report_data["branch_info"]["generated_at"]]
            ], columns=["Metric", "Value"])
            
            branch_df.to_excel(writer, sheet_name='Branch Info', index=False)
            
            # Financial Summary Sheet
            financial_data = report_data["financial_metrics"]["period_summary"]
            financial_df = pd.DataFrame([
                ["Loans Disbursed", financial_data["loans_disbursed"]],
                ["Amount Disbursed", financial_data["amount_disbursed"]],
                ["Payments Received", financial_data["payments_received"]],
                ["Amount Collected", financial_data["amount_collected"]],
                ["Collection Rate", f"{financial_data['collection_rate']:.2f}%"]
            ], columns=["Metric", "Value"])
            
            financial_df.to_excel(writer, sheet_name='Financial Summary', index=False)
            
            # Customer Analytics Sheet
            if "customer_analytics" in report_data:
                customer_data = report_data["customer_analytics"]
                customer_df = pd.DataFrame([
                    ["Total Customers", customer_data["total_customers"]],
                    ["New Customers", customer_data["customer_segments"]["new_customers"]],
                    ["Active Customers", customer_data["customer_segments"]["active_customers"]],
                    ["Dormant Customers", customer_data["customer_segments"]["dormant_customers"]],
                    ["High Value Customers", customer_data["customer_segments"]["high_value_customers"]],
                    ["Average Loan Size", f"KES {customer_data['customer_behavior']['avg_loan_size']:,.2f}"],
                    ["Average Savings", f"KES {customer_data['customer_behavior']['avg_savings_balance']:,.2f}"]
                ], columns=["Metric", "Value"])
                
                customer_df.to_excel(writer, sheet_name='Customer Analytics', index=False)
            
            # Portfolio Analysis Sheet
            if "portfolio_analysis" in report_data:
                portfolio_data = report_data["portfolio_analysis"]
                portfolio_df = pd.DataFrame([
                    ["Active Loans", portfolio_data.get("active_loans", 0)],
                    ["Completed Loans", portfolio_data.get("completed_loans", 0)],
                    ["Arrears Loans", portfolio_data.get("arrears_loans", 0)],
                    ["Total Outstanding", f"KES {portfolio_data.get('total_outstanding', 0):,.2f}"],
                    ["PAR 30", f"KES {portfolio_data.get('par_30', 0):,.2f}"],
                    ["PAR 90", f"KES {portfolio_data.get('par_90', 0):,.2f}"]
                ], columns=["Metric", "Value"])
                
                portfolio_df.to_excel(writer, sheet_name='Portfolio Analysis', index=False)
        
        return file_path
    
    def generate_individual_statement(self, user_id: int, 
                                   start_date: date, end_date: date,
                                   format: str = "pdf") -> Dict[str, Any]:
        """Generate individual customer statement"""
        db = SessionLocal()
        try:
            # Get customer
            customer = db.query(User).filter(User.id == user_id).first()
            if not customer:
                return {"error": "Customer not found"}
            
            # Get account information
            savings_account = customer.savings_account
            drawdown_account = customer.drawdown_account
            
            # Get loans
            customer_loans = db.query(Loan).filter(
                Loan.borrower_id == user_id,
                Loan.start_date >= start_date,
                Loan.start_date <= end_date
            ).all()
            
            # Get payments
            customer_payments = db.query(Payment).join(Loan).filter(
                Loan.borrower_id == user_id,
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
                Payment.status == 'confirmed'
            ).all()
            
            # Get transactions
            from app.models.loan import Transaction
            customer_transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.created_at >= datetime.combine(start_date, datetime.min.time()),
                Transaction.created_at <= datetime.combine(end_date, datetime.max.time())
            ).all()
            
            statement_data = {
                "customer_info": {
                    "name": f"{customer.first_name} {customer.last_name}",
                    "phone": customer.phone_number,
                    "account_number": customer.unique_account_number,
                    "statement_period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                },
                "account_summary": {
                    "savings_balance": float(savings_account.balance) if savings_account else 0,
                    "drawdown_balance": float(drawdown_account.balance) if drawdown_account else 0,
                    "loan_limit": float(savings_account.loan_limit) if savings_account else 0,
                    "registration_status": savings_account.status if savings_account else "inactive"
                },
                "loans": [
                    {
                        "loan_number": loan.loan_number,
                        "amount": float(loan.total_amount),
                        "balance": float(loan.balance),
                        "status": loan.status,
                        "start_date": loan.start_date.strftime('%Y-%m-%d'),
                        "due_date": loan.due_date.strftime('%Y-%m-%d')
                    }
                    for loan in customer_loans
                ],
                "payments": [
                    {
                        "payment_number": payment.payment_number,
                        "amount": float(payment.amount),
                        "loan_number": payment.loan.loan_number,
                        "payment_date": payment.payment_date.strftime('%Y-%m-%d'),
                        "method": payment.payment_method
                    }
                    for payment in customer_payments
                ],
                "transactions": [
                    {
                        "transaction_number": tx.transaction_number,
                        "type": tx.transaction_type,
                        "account": tx.account_type,
                        "amount": float(tx.amount),
                        "balance_after": float(tx.balance_after),
                        "date": tx.created_at.strftime('%Y-%m-%d %H:%M'),
                        "description": tx.description
                    }
                    for tx in customer_transactions
                ]
            }
            
            # Export based on format
            if format.lower() == "pdf":
                file_path = self._export_statement_to_pdf(statement_data)
            elif format.lower() == "excel":
                file_path = self._export_statement_to_excel(statement_data)
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "customer_name": statement_data["customer_info"]["name"]
            }
            
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()
    
    def _export_statement_to_pdf(self, statement_data: Dict[str, Any]) -> str:
        """Export customer statement to PDF"""
        
        customer_name = statement_data["customer_info"]["name"].replace(" ", "_")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"statement_{customer_name}_{timestamp}.pdf"
        file_path = os.path.join(self.reports_dir, filename)
        
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Header
        story.append(Paragraph("Kim Loans Management System", styles['Title']))
        story.append(Paragraph("Customer Account Statement", styles['Heading1']))
        story.append(Spacer(1, 20))
        
        # Customer Info
        customer_info = statement_data["customer_info"]
        info_data = [
            ["Customer Name", customer_info["name"]],
            ["Phone Number", customer_info["phone"]],
            ["Account Number", customer_info["account_number"]],
            ["Statement Period", customer_info["statement_period"]]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10)
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Account Summary
        story.append(Paragraph("Account Summary", styles['Heading2']))
        account_data = statement_data["account_summary"]
        
        summary_data = [
            ["Account Type", "Balance", "Status"],
            ["Savings Account", f"KES {account_data['savings_balance']:,.2f}", account_data["registration_status"]],
            ["Drawdown Account", f"KES {account_data['drawdown_balance']:,.2f}", "Active"],
            ["Available Loan Limit", f"KES {account_data['loan_limit']:,.2f}", "Current"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER')
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Loans Section
        if statement_data["loans"]:
            story.append(Paragraph("Active Loans", styles['Heading2']))
            
            loans_data = [["Loan Number", "Amount", "Balance", "Status", "Due Date"]]
            for loan in statement_data["loans"]:
                loans_data.append([
                    loan["loan_number"],
                    f"KES {loan['amount']:,.2f}",
                    f"KES {loan['balance']:,.2f}",
                    loan["status"].title(),
                    loan["due_date"]
                ])
            
            loans_table = Table(loans_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1*inch, 1.1*inch])
            loans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 9)
            ]))
            
            story.append(loans_table)
            story.append(Spacer(1, 20))
        
        # Payments Section
        if statement_data["payments"]:
            story.append(Paragraph("Payment History", styles['Heading2']))
            
            payments_data = [["Payment #", "Amount", "Loan #", "Date", "Method"]]
            for payment in statement_data["payments"]:
                payments_data.append([
                    payment["payment_number"],
                    f"KES {payment['amount']:,.2f}",
                    payment["loan_number"],
                    payment["payment_date"],
                    payment["method"].title()
                ])
            
            payments_table = Table(payments_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1*inch, 1.1*inch])
            payments_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightyellow),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 9)
            ]))
            
            story.append(payments_table)
        
        # Build PDF
        doc.build(story)
        
        return file_path
    
    def generate_system_report(self, report_type: str, 
                             parameters: Dict[str, Any],
                             format: str = "pdf") -> Dict[str, Any]:
        """Generate system-wide reports"""
        
        if report_type == "all_branches_comparison":
            return self._generate_branches_comparison_report(parameters, format)
        elif report_type == "loan_portfolio_analysis":
            return self._generate_portfolio_analysis_report(parameters, format)
        elif report_type == "risk_assessment":
            return self._generate_risk_assessment_report(parameters, format)
        elif report_type == "profitability_analysis":
            return self._generate_profitability_report(parameters, format)
        else:
            return {"error": "Unknown report type"}
    
    def _generate_branches_comparison_report(self, parameters: Dict[str, Any], 
                                          format: str) -> Dict[str, Any]:
        """Generate comparative analysis of all branches"""
        db = SessionLocal()
        try:
            # Get all branches
            branches = db.query(Branch).filter(Branch.is_active == True).all()
            
            comparison_data = []
            
            for branch in branches:
                # Get branch analytics
                branch_analytics = analytics_engine.generate_comprehensive_analytics(
                    branch_id=branch.id,
                    user_role=UserRole.ADMIN
                )
                
                if "error" not in branch_analytics:
                    overview = branch_analytics["overview"]
                    
                    comparison_data.append({
                        "branch_id": branch.id,
                        "branch_name": branch.name,
                        "branch_code": branch.code,
                        "manager": f"{branch.manager.first_name} {branch.manager.last_name}" if branch.manager else "Not Assigned",
                        "total_customers": overview["total_customers"],
                        "active_loans": overview["active_loans"],
                        "total_disbursed": overview["total_disbursed"],
                        "total_collected": overview["total_collected"],
                        "collection_rate": overview["collection_rate"],
                        "par_ratio": overview["par_ratio"],
                        "total_savings": overview["total_savings"],
                        "gross_profit": overview.get("gross_profit", 0)
                    })
            
            # Create comparison analysis
            if comparison_data:
                # Rankings
                best_collection = max(comparison_data, key=lambda x: x["collection_rate"])
                best_growth = max(comparison_data, key=lambda x: x["total_disbursed"])
                lowest_risk = min(comparison_data, key=lambda x: x["par_ratio"])
                
                analysis = {
                    "branches_data": comparison_data,
                    "rankings": {
                        "best_collection_rate": {
                            "branch": best_collection["branch_name"],
                            "rate": best_collection["collection_rate"]
                        },
                        "highest_disbursement": {
                            "branch": best_growth["branch_name"],
                            "amount": best_growth["total_disbursed"]
                        },
                        "lowest_risk": {
                            "branch": lowest_risk["branch_name"],
                            "par_ratio": lowest_risk["par_ratio"]
                        }
                    },
                    "system_totals": {
                        "total_branches": len(comparison_data),
                        "total_customers": sum(b["total_customers"] for b in comparison_data),
                        "total_disbursed": sum(b["total_disbursed"] for b in comparison_data),
                        "total_collected": sum(b["total_collected"] for b in comparison_data),
                        "system_collection_rate": (sum(b["total_collected"] for b in comparison_data) / 
                                                 sum(b["total_disbursed"] for b in comparison_data) * 100) if sum(b["total_disbursed"] for b in comparison_data) > 0 else 0
                    }
                }
                
                # Export to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"branches_comparison_{timestamp}.{format}"
                file_path = os.path.join(self.reports_dir, filename)
                
                if format == "excel":
                    # Export to Excel
                    df = pd.DataFrame(comparison_data)
                    df.to_excel(file_path, index=False)
                elif format == "pdf":
                    # Export to PDF (simplified)
                    doc = SimpleDocTemplate(file_path, pagesize=A4)
                    story = []
                    story.append(Paragraph("Branches Comparison Report", getSampleStyleSheet()['Title']))
                    # Add table with branch data
                    # (Simplified implementation)
                    doc.build(story)
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "analysis": analysis
                }
            else:
                return {"error": "No branch data available"}
                
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()


# Initialize reporting engine
reporting_engine = ReportingEngine()