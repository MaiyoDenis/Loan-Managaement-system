"""
Advanced Reporting Engine with PDF/Excel Export
Generates comprehensive reports for all system data with beautiful formatting
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import io
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models.loan import Loan, Payment, SavingsAccount, BranchInventory
from app.models.user import User
from app.models.branch import Branch, Group
from app.core.permissions import UserRole
from app.services.analytics import analytics_engine


class ReportingEngine:
    """
    Advanced reporting engine with AI-powered insights
    Generates PDF, Excel, and interactive reports
    """
    
    def __init__(self):
        self.db = SessionLocal()
        self.reports_dir = "reports"
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Set up matplotlib for chart generation
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    # ==================== COMPREHENSIVE LOAN REPORTS ====================
    
    def generate_branch_performance_report(self, branch_id: int, 
                                         start_date: date, end_date: date,
                                         format: str = "pdf") -> Dict[str, Any]:
        """
        Generate comprehensive branch performance report
        Includes: Loans, Payments, Customers, Risk Analysis, Recommendations
        """
        try:
            # Get branch data
            branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
            if not branch:
                return {"error": "Branch not found"}
            
            # Collect comprehensive data
            report_data = self._collect_branch_data(branch_id, start_date, end_date)
            
            # Generate insights using AI
            insights = self._generate_branch_insights(report_data)
            
            # Create report based on format
            if format.lower() == "pdf":
                file_path = self._create_pdf_branch_report(branch, report_data, insights)
            elif format.lower() == "excel":
                file_path = self._create_excel_branch_report(branch, report_data, insights)
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "report_type": "branch_performance",
                "branch_name": branch.name,
                "period": f"{start_date} to {end_date}",
                "generated_at": datetime.utcnow().isoformat(),
                "insights_summary": insights["summary"]
            }
            
        except Exception as e:
            logger.error(f"Error generating branch report: {e}")
            return {"error": str(e)}
    
    def generate_customer_portfolio_report(self, customer_id: int, format: str = "pdf") -> Dict[str, Any]:
        """Generate detailed customer portfolio report with risk analysis"""
        try:
            customer = self.db.query(User).filter(User.id == customer_id).first()
            if not customer:
                return {"error": "Customer not found"}
            
            # Collect customer data
            customer_data = self._collect_customer_data(customer_id)
            
            # Get risk analysis
            risk_analysis = analytics_engine.calculate_customer_risk_score(customer_id)
            
            # Generate report
            if format.lower() == "pdf":
                file_path = self._create_pdf_customer_report(customer, customer_data, risk_analysis)
            elif format.lower() == "excel":
                file_path = self._create_excel_customer_report(customer, customer_data, risk_analysis)
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "report_type": "customer_portfolio",
                "customer_name": f"{customer.first_name} {customer.last_name}",
                "risk_score": risk_analysis.get("risk_score", 0),
                "risk_category": risk_analysis.get("risk_category", "Unknown"),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating customer report: {e}")
            return {"error": str(e)}
    
    def generate_financial_summary_report(self, branch_id: Optional[int] = None,
                                        start_date: Optional[date] = None,
                                        end_date: Optional[date] = None,
                                        format: str = "pdf") -> Dict[str, Any]:
        """Generate organization-wide financial summary with executive insights"""
        try:
            # Set default date range (last 3 months)
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=90)
            
            # Collect financial data
            financial_data = self._collect_financial_summary_data(branch_id, start_date, end_date)
            
            # Generate executive insights
            executive_insights = self._generate_executive_insights(financial_data)
            
            # Create report
            if format.lower() == "pdf":
                file_path = self._create_pdf_financial_report(financial_data, executive_insights, start_date, end_date)
            elif format.lower() == "excel":
                file_path = self._create_excel_financial_report(financial_data, executive_insights, start_date, end_date)
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "report_type": "financial_summary",
                "scope": "Organization-wide" if not branch_id else f"Branch {branch_id}",
                "period": f"{start_date} to {end_date}",
                "total_portfolio": financial_data["summary"]["total_portfolio"],
                "collection_rate": financial_data["summary"]["collection_rate"],
                "generated_at": datetime.utcnow().isoformat(),
                "executive_summary": executive_insights["key_points"]
            }
            
        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {"error": str(e)}
    
    # ==================== DATA COLLECTION METHODS ====================
    
    def _collect_branch_data(self, branch_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        """Collect comprehensive branch data for reporting"""
        
        # Get branch customers
        branch_customers = self.db.query(User).filter(
            User.branch_id == branch_id,
            User.role == UserRole.CUSTOMER
        ).all()
        
        customer_ids = [c.id for c in branch_customers]
        
        # Loan data
        branch_loans = self.db.query(Loan).filter(
            Loan.borrower_id.in_(customer_ids),
            Loan.created_at.between(start_date, end_date)
        ).all()
        
        # Payment data
        branch_payments = self.db.query(Payment).join(Loan).filter(
            Loan.borrower_id.in_(customer_ids),
            Payment.payment_date.between(start_date, end_date),
            Payment.status == "confirmed"
        ).all()
        
        # Savings data
        branch_savings = self.db.query(SavingsAccount).filter(
            SavingsAccount.user_id.in_(customer_ids)
        ).all()
        
        # Group data
        branch_groups = self.db.query(Group).filter(
            Group.branch_id == branch_id
        ).all()
        
        # Inventory data
        branch_inventory = self.db.query(BranchInventory).filter(
            BranchInventory.branch_id == branch_id
        ).all()
        
        return {
            "branch_id": branch_id,
            "period": {"start": start_date, "end": end_date},
            "customers": branch_customers,
            "loans": branch_loans,
            "payments": branch_payments,
            "savings": branch_savings,
            "groups": branch_groups,
            "inventory": branch_inventory,
            "summary": {
                "total_customers": len(branch_customers),
                "total_loans": len(branch_loans),
                "active_loans": len([l for l in branch_loans if l.status == "active"]),
                "completed_loans": len([l for l in branch_loans if l.status == "completed"]),
                "arrears_loans": len([l for l in branch_loans if l.status == "arrears"]),
                "total_disbursed": sum(float(loan.total_amount) for loan in branch_loans),
                "total_collected": sum(float(payment.amount) for payment in branch_payments),
                "total_savings": sum(float(acc.balance) for acc in branch_savings),
                "total_groups": len(branch_groups),
                "inventory_value": sum(
                    float(item.loan_product.selling_price) * item.current_quantity
                    for item in branch_inventory
                )
            }
        }
    
    def _collect_customer_data(self, customer_id: int) -> Dict[str, Any]:
        """Collect comprehensive customer data"""
        
        customer = self.db.query(User).filter(User.id == customer_id).first()
        
        # Get customer's loans
        customer_loans = self.db.query(Loan).filter(
            Loan.borrower_id == customer_id
        ).all()
        
        # Get payment history
        customer_payments = self.db.query(Payment).join(Loan).filter(
            Loan.borrower_id == customer_id,
            Payment.status == "confirmed"
        ).order_by(Payment.payment_date.desc()).all()
        
        # Get account data
        savings_account = customer.savings_account
        drawdown_account = customer.drawdown_account
        
        # Get transaction history
        from app.models.loan import Transaction
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == customer_id
        ).order_by(Transaction.created_at.desc()).limit(50).all()
        
        return {
            "customer": customer,
            "loans": customer_loans,
            "payments": customer_payments,
            "savings_account": savings_account,
            "drawdown_account": drawdown_account,
            "transactions": transactions,
            "summary": {
                "total_loans": len(customer_loans),
                "active_loans": len([l for l in customer_loans if l.status == "active"]),
                "completed_loans": len([l for l in customer_loans if l.status == "completed"]),
                "total_borrowed": sum(float(loan.total_amount) for loan in customer_loans),
                "total_paid": sum(float(payment.amount) for payment in customer_payments),
                "current_balance": sum(float(loan.balance) for loan in customer_loans if loan.status in ["active", "arrears"]),
                "savings_balance": float(savings_account.balance) if savings_account else 0,
                "drawdown_balance": float(drawdown_account.balance) if drawdown_account else 0
            }
        }
    
    def _collect_financial_summary_data(self, branch_id: Optional[int], 
                                      start_date: date, end_date: date) -> Dict[str, Any]:
        """Collect organization-wide financial data"""
        
        # Base queries
        user_query = self.db.query(User).filter(User.role == UserRole.CUSTOMER)
        loan_query = self.db.query(Loan)
        payment_query = self.db.query(Payment).filter(Payment.status == "confirmed")
        
        # Apply branch filtering if specified
        if branch_id:
            branch_customers = user_query.filter(User.branch_id == branch_id).all()
            customer_ids = [c.id for c in branch_customers]
            loan_query = loan_query.filter(Loan.borrower_id.in_(customer_ids))
            payment_query = payment_query.join(Loan).filter(Loan.borrower_id.in_(customer_ids))
        
        # Apply date filtering
        loan_query = loan_query.filter(Loan.created_at.between(start_date, end_date))
        payment_query = payment_query.filter(Payment.payment_date.between(start_date, end_date))
        
        # Execute queries
        all_customers = user_query.all()
        period_loans = loan_query.all()
        period_payments = payment_query.all()
        
        # Calculate comprehensive metrics
        total_customers = len(all_customers)
        total_loans_disbursed = len(period_loans)
        total_amount_disbursed = sum(float(loan.total_amount) for loan in period_loans)
        total_payments_received = len(period_payments)
        total_amount_collected = sum(float(payment.amount) for payment in period_payments)
        
        # Collection rate
        collection_rate = (total_amount_collected / total_amount_disbursed * 100) if total_amount_disbursed > 0 else 0
        
        # Active portfolio
        active_loans = [loan for loan in period_loans if loan.status == "active"]
        arrears_loans = [loan for loan in period_loans if loan.status == "arrears"]
        completed_loans = [loan for loan in period_loans if loan.status == "completed"]
        
        outstanding_balance = sum(float(loan.balance) for loan in active_loans + arrears_loans)
        arrears_amount = sum(float(loan.balance) for loan in arrears_loans)
        
        # Branch breakdown
        branch_breakdown = []
        if not branch_id:  # Organization-wide report
            branches = self.db.query(Branch).filter(Branch.is_active == True).all()
            for branch in branches:
                branch_kpis = analytics_engine._calculate_branch_kpis(branch.id)
                branch_breakdown.append({
                    "branch_id": branch.id,
                    "branch_name": branch.name,
                    "manager_name": f"{branch.manager.first_name} {branch.manager.last_name}" if branch.manager else "No Manager",
                    **branch_kpis
                })
        
        # Product performance
        from app.models.loan import LoanProduct, LoanApplicationProduct
        
        product_performance = []
        products = self.db.query(LoanProduct).filter(LoanProduct.is_active == True).all()
        
        for product in products:
            # Get loan applications with this product in the period
            product_applications = self.db.query(LoanApplicationProduct).join(
                LoanApplication
            ).filter(
                LoanApplicationProduct.loan_product_id == product.id,
                LoanApplication.created_at.between(start_date, end_date)
            ).all()
            
            total_quantity = sum(app.quantity for app in product_applications)
            total_value = sum(float(app.total_price) for app in product_applications)
            
            product_performance.append({
                "product_id": product.id,
                "product_name": product.name,
                "category_name": product.category.name,
                "total_loans": len(product_applications),
                "total_quantity": total_quantity,
                "total_value": total_value,
                "avg_loan_size": total_value / len(product_applications) if product_applications else 0
            })
        
        return {
            "summary": {
                "total_customers": total_customers,
                "total_loans": total_loans_disbursed,
                "total_amount_disbursed": total_amount_disbursed,
                "total_payments": total_payments_received,
                "total_amount_collected": total_amount_collected,
                "collection_rate": round(collection_rate, 2),
                "outstanding_balance": outstanding_balance,
                "arrears_amount": arrears_amount,
                "arrears_rate": round((arrears_amount / outstanding_balance * 100) if outstanding_balance > 0 else 0, 2)
            },
            "loan_breakdown": {
                "active": len(active_loans),
                "completed": len(completed_loans),
                "arrears": len(arrears_loans)
            },
            "branch_breakdown": branch_breakdown,
            "product_performance": sorted(product_performance, key=lambda x: x["total_value"], reverse=True),
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()}
        }
    
    def generate_risk_assessment_report(self, branch_id: Optional[int] = None,
                                      format: str = "pdf") -> Dict[str, Any]:
        """Generate comprehensive risk assessment report with predictive analytics"""
        try:
            # Get customers for analysis
            customer_query = self.db.query(User).filter(User.role == UserRole.CUSTOMER)
            
            if branch_id:
                customer_query = customer_query.filter(User.branch_id == branch_id)
            
            customers = customer_query.all()
            
            # Analyze each customer
            risk_assessments = []
            risk_distribution = {"very_low": 0, "low": 0, "medium": 0, "high": 0, "very_high": 0}
            
            for customer in customers:
                risk_data = analytics_engine.calculate_customer_risk_score(customer.id)
                
                if "error" not in risk_data:
                    risk_assessments.append(risk_data)
                    
                    # Categorize risk
                    score = risk_data["risk_score"]
                    if score >= 80:
                        risk_distribution["very_low"] += 1
                    elif score >= 65:
                        risk_distribution["low"] += 1
                    elif score >= 50:
                        risk_distribution["medium"] += 1
                    elif score >= 35:
                        risk_distribution["high"] += 1
                    else:
                        risk_distribution["very_high"] += 1
            
            # Sort by risk score (highest risk first)
            risk_assessments.sort(key=lambda x: x["risk_score"])
            
            # Calculate portfolio risk metrics
            if risk_assessments:
                avg_risk_score = np.mean([ra["risk_score"] for ra in risk_assessments])
                risk_variance = np.var([ra["risk_score"] for ra in risk_assessments])
                
                # High-risk customers (score < 40)
                high_risk_customers = [ra for ra in risk_assessments if ra["risk_score"] < 40]
                
                # Get their total outstanding loans
                high_risk_ids = [ra["customer_id"] for ra in high_risk_customers]
                high_risk_loans = self.db.query(Loan).filter(
                    Loan.borrower_id.in_(high_risk_ids),
                    Loan.status.in_(["active", "arrears"])
                ).all()
                
                high_risk_amount = sum(float(loan.balance) for loan in high_risk_loans)
            else:
                avg_risk_score = 0
                risk_variance = 0
                high_risk_amount = 0
                high_risk_customers = []
            
            # Generate forecasts
            arrears_forecast = analytics_engine.forecast_arrears_risk(30, branch_id)
            
            # Create report
            if format.lower() == "pdf":
                file_path = self._create_pdf_risk_report(
                    risk_assessments, risk_distribution, arrears_forecast
                )
            elif format.lower() == "excel":
                file_path = self._create_excel_risk_report(
                    risk_assessments, risk_distribution, arrears_forecast
                )
            else:
                return {"error": "Unsupported format"}
            
            return {
                "success": True,
                "file_path": file_path,
                "report_type": "risk_assessment",
                "scope": "Organization-wide" if not branch_id else f"Branch {branch_id}",
                "total_customers_analyzed": len(risk_assessments),
                "average_risk_score": round(avg_risk_score, 2),
                "high_risk_customers": len(high_risk_customers),
                "amount_at_high_risk": high_risk_amount,
                "risk_distribution": risk_distribution,
                "predicted_arrears_amount": arrears_forecast.get("summary", {}).get("predicted_arrears_amount", 0),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating risk assessment report: {e}")
            return {"error": str(e)}
    
    # ==================== AI INSIGHTS GENERATION ====================
    
    def _generate_branch_insights(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered insights for branch performance"""
        
        summary = report_data["summary"]
        
        insights = {
            "performance_rating": "",
            "key_strengths": [],
            "areas_for_improvement": [],
            "strategic_recommendations": [],
            "risk_alerts": [],
            "growth_opportunities": []
        }
        
        # Performance rating
        collection_rate = summary["collection_rate"]
        if collection_rate >= 95:
            insights["performance_rating"] = "Excellent"
        elif collection_rate >= 85:
            insights["performance_rating"] = "Good"
        elif collection_rate >= 75:
            insights["performance_rating"] = "Average"
        else:
            insights["performance_rating"] = "Needs Improvement"
        
        # Identify strengths
        if collection_rate >= 90:
            insights["key_strengths"].append(f"Outstanding collection rate of {collection_rate:.1f}%")
        
        if summary["arrears_rate"] <= 5:
            insights["key_strengths"].append(f"Low arrears rate of {summary['arrears_rate']:.1f}%")
        
        if summary["total_customers"] >= 100:
            insights["key_strengths"].append(f"Strong customer base of {summary['total_customers']} customers")
        
        # Identify improvement areas
        if collection_rate < 80:
            insights["areas_for_improvement"].append("Collection rate below industry standard")
            insights["strategic_recommendations"].append("Implement stricter credit assessment and follow-up procedures")
        
        if summary["arrears_rate"] > 10:
            insights["areas_for_improvement"].append("High arrears rate indicating collection challenges")
            insights["strategic_recommendations"].append("Deploy dedicated collection team and early intervention strategies")
        
        # Growth opportunities
        avg_loan_size = summary["total_disbursed"] / summary["total_loans"] if summary["total_loans"] > 0 else 0
        if avg_loan_size < 5000:
            insights["growth_opportunities"].append("Opportunity to increase average loan size through customer education")
        
        if summary["total_savings"] / summary["total_customers"] < 2000:
            insights["growth_opportunities"].append("Focus on savings mobilization to increase loan capacity")
        
        return insights
    
    def _generate_executive_insights(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive-level insights for financial report"""
        
        summary = financial_data["summary"]
        
        insights = {
            "key_points": [],
            "critical_actions": [],
            "investment_recommendations": [],
            "risk_mitigation": [],
            "growth_strategy": []
        }
        
        # Key performance points
        insights["key_points"].append(
            f"Portfolio size: KES {summary['total_portfolio']:,.2f} across {summary['total_loans']} loans"
        )
        insights["key_points"].append(
            f"Collection efficiency: {summary['collection_rate']:.1f}% with {summary['total_payments']} payments processed"
        )
        
        # Critical actions based on performance
        if summary["collection_rate"] < 85:
            insights["critical_actions"].append("Immediate focus required on collection processes")
        
        if summary["arrears_rate"] > 15:
            insights["critical_actions"].append("Deploy emergency arrears management protocol")
        
        # Investment recommendations
        if summary["collection_rate"] > 90 and summary["arrears_rate"] < 5:
            insights["investment_recommendations"].append("Portfolio performance supports expansion into new markets")
            insights["investment_recommendations"].append("Consider increasing loan limits and introducing new products")
        
        # Risk mitigation
        if summary["arrears_amount"] > summary["total_portfolio"] * 0.1:
            insights["risk_mitigation"].append("Implement enhanced credit scoring and early warning systems")
        
        return insights
    
    # ==================== PDF REPORT GENERATION ====================
    
    def _create_pdf_branch_report(self, branch: Branch, report_data: Dict[str, Any], 
                                insights: Dict[str, Any]) -> str:
        """Create beautifully formatted PDF branch report"""
        
        filename = f"branch_report_{branch.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
            textColor=colors.darkblue,
            alignment=1  # Center alignment
        )
        
        story.append(Paragraph("Kim Loans Management System", title_style))
        story.append(Paragraph(f"Branch Performance Report - {branch.name}", styles['Heading2']))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", styles['Heading2']))
        summary = report_data["summary"]
        
        summary_data = [
            ["Metric", "Value", "Performance"],
            ["Total Customers", f"{summary['total_customers']:,}", "📊"],
            ["Active Loans", f"{summary['active_loans']:,}", "💰"],
            ["Collection Rate", f"{summary['collection_rate']:.1f}%", "📈"],
            ["Total Portfolio", f"KES {summary['total_disbursed']:,.2f}", "🏦"],
            ["Arrears Rate", f"{report_data.get('arrears_rate', 0):.1f}%", "⚠️"]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Performance Insights
        story.append(Paragraph("AI-Powered Performance Insights", styles['Heading2']))
        story.append(Paragraph(f"Overall Rating: {insights['performance_rating']}", styles['Heading3']))
        
        # Key Strengths
        if insights["key_strengths"]:
            story.append(Paragraph("Key Strengths:", styles['Heading4']))
            for strength in insights["key_strengths"]:
                story.append(Paragraph(f"✅ {strength}", styles['Normal']))
            story.append(Spacer(1, 10))
        
        # Areas for Improvement
        if insights["areas_for_improvement"]:
            story.append(Paragraph("Areas for Improvement:", styles['Heading4']))
            for improvement in insights["areas_for_improvement"]:
                story.append(Paragraph(f"🔧 {improvement}", styles['Normal']))
            story.append(Spacer(1, 10))
        
        # Strategic Recommendations
        if insights["strategic_recommendations"]:
            story.append(Paragraph("Strategic Recommendations:", styles['Heading4']))
            for recommendation in insights["strategic_recommendations"]:
                story.append(Paragraph(f"🎯 {recommendation}", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return file_path
    
    def _create_excel_branch_report(self, branch: Branch, report_data: Dict[str, Any], 
                                  insights: Dict[str, Any]) -> str:
        """Create comprehensive Excel branch report with multiple sheets"""
        
        filename = f"branch_report_{branch.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = os.path.join(self.reports_dir, filename)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            
            # Summary Sheet
            summary_data = {
                "Metric": ["Total Customers", "Active Loans", "Completed Loans", "Arrears Loans", 
                          "Total Disbursed", "Total Collected", "Collection Rate", "Outstanding Balance"],
                "Value": [
                    report_data["summary"]["total_customers"],
                    report_data["summary"]["active_loans"],
                    report_data["summary"]["completed_loans"],
                    report_data["summary"]["arrears_loans"],
                    f"KES {report_data['summary']['total_disbursed']:,.2f}",
                    f"KES {report_data['summary']['total_collected']:,.2f}",
                    f"{report_data['summary']['collection_rate']:.2f}%",
                    f"KES {report_data['summary']['outstanding_balance']:,.2f}"
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Loans Sheet
            loans_data = []
            for loan in report_data["loans"]:
                loans_data.append({
                    "Loan Number": loan.loan_number,
                    "Borrower": f"{loan.borrower.first_name} {loan.borrower.last_name}",
                    "Total Amount": float(loan.total_amount),
                    "Amount Paid": float(loan.amount_paid),
                    "Balance": float(loan.balance),
                    "Status": loan.status.value,
                    "Start Date": loan.start_date.isoformat(),
                    "Due Date": loan.due_date.isoformat(),
                    "Payment Progress": f"{(float(loan.amount_paid) / float(loan.total_amount) * 100):.1f}%"
                })
            
            if loans_data:
                loans_df = pd.DataFrame(loans_data)
                loans_df.to_excel(writer, sheet_name='Loans', index=False)
            
            # Payments Sheet
            payments_data = []
            for payment in report_data["payments"]:
                payments_data.append({
                    "Payment Number": payment.payment_number,
                    "Loan Number": payment.loan.loan_number,
                    "Customer": f"{payment.payer.first_name} {payment.payer.last_name}",
                    "Amount": float(payment.amount),
                    "Method": payment.payment_method,
                    "Date": payment.payment_date.isoformat(),
                    "Status": payment.status.value
                })
            
            if payments_data:
                payments_df = pd.DataFrame(payments_data)
                payments_df.to_excel(writer, sheet_name='Payments', index=False)
            
            # Insights Sheet
            insights_data = {
                "Category": ["Performance Rating"] + ["Strength"] * len(insights["key_strengths"]) + 
                           ["Improvement Area"] * len(insights["areas_for_improvement"]) +
                           ["Recommendation"] * len(insights["strategic_recommendations"]),
                "Description": [insights["performance_rating"]] + insights["key_strengths"] + 
                              insights["areas_for_improvement"] + insights["strategic_recommendations"]
            }
            
            insights_df = pd.DataFrame(insights_data)
            insights_df.to_excel(writer, sheet_name='AI Insights', index=False)
        
        return file_path


# Initialize reporting engine
reporting_engine = ReportingEngine()