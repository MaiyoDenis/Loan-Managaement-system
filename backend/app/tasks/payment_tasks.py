"""
Background tasks for payment processing using Celery
"""

from celery import Celery
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import List, Optional

from app.database import SessionLocal
from app.models.loan import (
    MpesaTransaction, 
    Payment, 
    Loan, 
    SavingsAccount, 
    DrawdownAccount,
    Transaction,
    Arrear
)
from app.models.user import User
from app.services.sms import sms_service, SMSTemplates
from app.services.notification import notification_service
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    'kim_loans_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Nairobi',
    enable_utc=True,
    beat_schedule={
        'process-automatic-payments': {
            'task': 'app.tasks.payment_tasks.process_automatic_payments',
            'schedule': 60.0,  # Every minute
        },
        'send-payment-reminders': {
            'task': 'app.tasks.payment_tasks.send_payment_reminders',
            'schedule': 3600.0,  # Every hour
        },
        'check-overdue-loans': {
            'task': 'app.tasks.payment_tasks.check_overdue_loans',
            'schedule': 1800.0,  # Every 30 minutes
        },
    },
)


@celery_app.task
def process_mpesa_payment_async(mpesa_transaction_id: int):
    """Process M-Pesa payment asynchronously"""
    db = SessionLocal()
    try:
        return process_mpesa_payment(db, mpesa_transaction_id)
    finally:
        db.close()


def process_mpesa_payment(db: Session, mpesa_transaction_id: int) -> dict:
    """Process confirmed M-Pesa payment"""
    
    # Get M-Pesa transaction
    mpesa_tx = db.query(MpesaTransaction).filter(
        MpesaTransaction.id == mpesa_transaction_id
    ).first()
    
    if not mpesa_tx or mpesa_tx.processed:
        return {"success": False, "error": "Transaction not found or already processed"}
    
    # Find customer by account number
    customer = db.query(User).filter(
        User.unique_account_number == mpesa_tx.account_number
    ).first()
    
    if not customer:
        mpesa_tx.processing_error = "Customer account not found"
        db.commit()
        return {"success": False, "error": "Customer account not found"}
    
    try:
        # Get customer's active loans (oldest first)
        active_loans = db.query(Loan).filter(
            Loan.borrower_id == customer.id,
            Loan.status.in_(["active", "arrears"]),
            Loan.balance > 0
        ).order_by(Loan.start_date.asc()).all()
        
        payment_amount = mpesa_tx.amount
        total_allocated = Decimal('0.00')
        payments_created = []
        
        # Allocate payment to loans
        for loan in active_loans:
            if payment_amount <= 0:
                break
            
            # Determine payment amount for this loan
            loan_payment = min(payment_amount, loan.balance)
            
            if loan_payment > 0:
                # Create payment record
                payment_number = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{customer.id}"
                
                payment = Payment(
                    payment_number=payment_number,
                    loan_id=loan.id,
                    payer_id=customer.id,
                    amount=loan_payment,
                    payment_method="mpesa",
                    mpesa_transaction_code=mpesa_tx.transaction_code,
                    status="confirmed",
                    confirmed_at=date.today(),
                    payment_date=date.today(),
                    auto_processed=True
                )
                
                db.add(payment)
                
                # Update loan balance
                loan.amount_paid += loan_payment
                loan.balance -= loan_payment
                
                # Check if loan is fully paid
                if loan.balance <= 0:
                    loan.status = "completed"
                    loan.balance = Decimal('0.00')
                
                # Update next payment date if partial payments allowed
                if loan.loan_type.allows_partial_payments and loan.balance > 0:
                    from dateutil.relativedelta import relativedelta
                    loan.next_payment_date = date.today() + relativedelta(months=1)
                
                payment_amount -= loan_payment
                total_allocated += loan_payment
                payments_created.append({
                    "loan_number": loan.loan_number,
                    "amount": float(loan_payment),
                    "remaining_balance": float(loan.balance)
                })
        
        # If there's remaining amount, add to savings account
        if payment_amount > 0:
            savings_account = customer.savings_account
            if savings_account:
                balance_before = savings_account.balance
                savings_account.balance += payment_amount
                
                # Handle registration fee payment
                if not savings_account.registration_fee_paid and savings_account.balance >= 0:
                    savings_account.registration_fee_paid = True
                    
                    # Send registration complete SMS
                    welcome_message = SMSTemplates.registration_complete(
                        customer.first_name,
                        customer.unique_account_number,
                        savings_account.loan_limit
                    )
                    await sms_service.send_sms(customer.phone_number, welcome_message)
                
                # Create transaction record
                transaction = Transaction(
                    transaction_number=f"MPESA{datetime.now().strftime('%Y%m%d%H%M%S')}{customer.id}",
                    user_id=customer.id,
                    account_id=savings_account.id,
                    account_type="savings",
                    transaction_type="deposit",
                    amount=payment_amount,
                    balance_before=balance_before,
                    balance_after=savings_account.balance,
                    description="M-Pesa payment - excess amount to savings",
                    reference_number=mpesa_tx.transaction_code
                )
                db.add(transaction)
        
        # Mark M-Pesa transaction as processed
        mpesa_tx.processed = True
        mpesa_tx.payment_allocation = payments_created
        
        db.commit()
        
        # Send confirmation SMS
        if payments_created:
            # Get primary loan payment for SMS
            primary_payment = payments_created[0]
            confirmation_message = SMSTemplates.payment_confirmation(
                customer.first_name,
                total_allocated,
                primary_payment["loan_number"],
                Decimal(str(primary_payment["remaining_balance"])),
                "Check app for details"
            )
        else:
            confirmation_message = f"Dear {customer.first_name}, KES {mpesa_tx.amount} received and added to your savings account. Thank you!"
        
        await sms_service.send_sms(customer.phone_number, confirmation_message)
        
        # Send notification to loan officer
        if customer.group_memberships:
            group = customer.group_memberships[0].group
            loan_officer = group.loan_officer
            
            await notification_service.send_notification(
                recipient_id=loan_officer.id,
                title="Payment Received",
                message=f"{customer.first_name} {customer.last_name} paid KES {mpesa_tx.amount}",
                notification_type="payment"
            )
        
        return {
            "success": True,
            "total_amount": float(mpesa_tx.amount),
            "loan_payments": payments_created,
            "savings_deposit": float(payment_amount) if payment_amount > 0 else 0
        }
        
    except Exception as e:
        mpesa_tx.processing_error = str(e)
        db.commit()
        return {"success": False, "error": str(e)}


@celery_app.task
def process_automatic_payments():
    """Process automatic loan payments from drawdown accounts"""
    db = SessionLocal()
    try:
        # Get loans due for payment today
        today = date.today()
        due_loans = db.query(Loan).filter(
            Loan.next_payment_date <= today,
            Loan.status == "active",
            Loan.balance > 0
        ).all()
        
        for loan in due_loans:
            # Get customer's drawdown account
            drawdown_account = loan.borrower.drawdown_account
            if not drawdown_account:
                continue
            
            # Check if sufficient balance for payment
            required_amount = loan.next_payment_amount or loan.balance
            
            if drawdown_account.balance >= required_amount:
                # Process automatic payment
                process_automatic_loan_payment(db, loan, required_amount)
            else:
                # Start grace period or move to arrears
                handle_insufficient_balance(db, loan, drawdown_account.balance)
        
        db.commit()
        
    except Exception as e:
        print(f"Error in automatic payments: {e}")
        db.rollback()
    finally:
        db.close()


def process_automatic_loan_payment(db: Session, loan: Loan, amount: Decimal):
    """Process automatic payment from drawdown account"""
    
    drawdown_account = loan.borrower.drawdown_account
    
    # Deduct from drawdown account
    balance_before = drawdown_account.balance
    drawdown_account.balance -= amount
    
    # Create payment record
    payment_number = f"AUTO{datetime.now().strftime('%Y%m%d%H%M%S')}{loan.borrower_id}"
    
    payment = Payment(
        payment_number=payment_number,
        loan_id=loan.id,
        payer_id=loan.borrower_id,
        amount=amount,
        payment_method="drawdown_auto",
        status="confirmed",
        confirmed_at=date.today(),
        payment_date=date.today(),
        auto_processed=True
    )
    
    db.add(payment)
    
    # Update loan
    loan.amount_paid += amount
    loan.balance -= amount
    
    if loan.balance <= 0:
        loan.status = "completed"
        loan.balance = Decimal('0.00')
    else:
        # Update next payment date
        if loan.loan_type.allows_partial_payments:
            from dateutil.relativedelta import relativedelta
            loan.next_payment_date = date.today() + relativedelta(months=1)
    
    # Create transaction record
    transaction = Transaction(
        transaction_number=f"AUTOPAY{datetime.now().strftime('%Y%m%d%H%M%S')}{loan.borrower_id}",
        user_id=loan.borrower_id,
        account_id=drawdown_account.id,
        account_type="drawdown",
        transaction_type="loan_repayment",
        amount=amount,
        balance_before=balance_before,
        balance_after=drawdown_account.balance,
        description=f"Automatic loan payment - {loan.loan_number}",
        reference_number=payment_number
    )
    
    db.add(transaction)
    
    # Send confirmation
    confirmation_message = SMSTemplates.payment_confirmation(
        loan.borrower.first_name,
        amount,
        loan.loan_number,
        loan.balance,
        loan.next_payment_date.strftime('%Y-%m-%d') if loan.next_payment_date else "N/A"
    )
    
    # Schedule SMS
    send_sms_async.delay(loan.borrower.phone_number, confirmation_message)


def handle_insufficient_balance(db: Session, loan: Loan, available_balance: Decimal):
    """Handle insufficient balance for automatic payment"""
    
    # Check if already in grace period
    existing_arrear = db.query(Arrear).filter(
        Arrear.loan_id == loan.id,
        Arrear.status == "grace_period"
    ).first()
    
    if existing_arrear:
        # Check if grace period expired
        grace_end = existing_arrear.grace_period_end
        if datetime.now() > grace_end:
            # Move to arrears
            existing_arrear.status = "arrears"
            loan.status = "arrears"
            
            # Send arrears notice
            arrears_message = SMSTemplates.arrears_notice(
                loan.borrower.first_name,
                loan.balance,
                loan.loan_number,
                (datetime.now().date() - loan.due_date).days
            )
            
            send_sms_async.delay(loan.borrower.phone_number, arrears_message)
    else:
        # Start grace period
        grace_end = datetime.now() + timedelta(minutes=settings.DEFAULT_GRACE_PERIOD_MINUTES)
        
        arrear = Arrear(
            loan_id=loan.id,
            amount_overdue=loan.next_payment_amount or loan.balance,
            days_overdue=0,
            grace_period_end=grace_end,
            status="grace_period"
        )
        
        db.add(arrear)
        
        # Send grace period notification
        grace_message = f"""Dear {loan.borrower.first_name},
Insufficient balance for automatic loan payment.

Loan: {loan.loan_number}
Required: KES {loan.next_payment_amount or loan.balance:,.2f}
Available: KES {available_balance:,.2f}

You have 60 minutes to add funds to your drawdown account.
- Kim Loans"""
        
        send_sms_async.delay(loan.borrower.phone_number, grace_message)


@celery_app.task
def send_payment_reminders():
    """Send payment reminders for upcoming due dates"""
    db = SessionLocal()
    try:
        # Get loans due in next 3 days
        from datetime import timedelta
        
        reminder_dates = [
            date.today() + timedelta(days=3),  # 3 days before
            date.today() + timedelta(days=1),  # 1 day before
            date.today()                        # Due today
        ]
        
        for reminder_date in reminder_dates:
            loans_due = db.query(Loan).filter(
                Loan.next_payment_date == reminder_date,
                Loan.status == "active",
                Loan.balance > 0
            ).all()
            
            for loan in loans_due:
                days_remaining = (reminder_date - date.today()).days
                
                reminder_message = SMSTemplates.payment_reminder(
                    loan.borrower.first_name,
                    loan.next_payment_amount or loan.balance,
                    loan.loan_number,
                    reminder_date.strftime('%Y-%m-%d'),
                    days_remaining
                )
                
                # Send SMS reminder
                send_sms_async.delay(loan.borrower.phone_number, reminder_message)
                
                # Send in-app notification
                send_notification_async.delay(
                    loan.borrower_id,
                    "Payment Reminder",
                    f"Your loan payment of KES {loan.next_payment_amount or loan.balance} is due in {days_remaining} days",
                    "reminder"
                )
        
    except Exception as e:
        print(f"Error sending payment reminders: {e}")
    finally:
        db.close()


@celery_app.task
def check_overdue_loans():
    """Check for overdue loans and manage arrears"""
    db = SessionLocal()
    try:
        today = date.today()
        
        # Get loans that are overdue
        overdue_loans = db.query(Loan).filter(
            Loan.due_date < today,
            Loan.status == "active",
            Loan.balance > 0
        ).all()
        
        for loan in overdue_loans:
            days_overdue = (today - loan.due_date).days
            
            # Check if arrear record exists
            existing_arrear = db.query(Arrear).filter(Arrear.loan_id == loan.id).first()
            
            if existing_arrear:
                # Update existing arrear
                existing_arrear.days_overdue = days_overdue
                existing_arrear.amount_overdue = loan.balance
            else:
                # Create new arrear record
                arrear = Arrear(
                    loan_id=loan.id,
                    amount_overdue=loan.balance,
                    days_overdue=days_overdue,
                    status="new"
                )
                db.add(arrear)
            
            # Update loan status
            loan.status = "arrears"
            
            # Send arrears notice (weekly)
            if days_overdue % 7 == 0:  # Every 7 days
                arrears_message = SMSTemplates.arrears_notice(
                    loan.borrower.first_name,
                    loan.balance,
                    loan.loan_number,
                    days_overdue
                )
                
                send_sms_async.delay(loan.borrower.phone_number, arrears_message)
        
        db.commit()
        
    except Exception as e:
        print(f"Error checking overdue loans: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task
def send_sms_async(phone_number: str, message: str, notification_id: Optional[int] = None):
    """Send SMS asynchronously"""
    return sms_service.send_sms(phone_number, message, notification_id)


@celery_app.task 
def send_notification_async(recipient_id: int, title: str, message: str, 
                          notification_type: str = "system"):
    """Send in-app notification asynchronously"""
    return notification_service.send_notification(
        recipient_id=recipient_id,
        title=title,
        message=message,
        notification_type=notification_type
    )


@celery_app.task
def send_bulk_notifications(recipients: List[int], title: str, message: str,
                          notification_type: str = "system", send_sms: bool = False):
    """Send notifications to multiple users"""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.id.in_(recipients)).all()
        
        for user in users:
            # Send in-app notification
            send_notification_async.delay(user.id, title, message, notification_type)
            
            # Send SMS if requested
            if send_sms and user.phone_number:
                send_sms_async.delay(user.phone_number, message)
        
        return {"success": True, "recipients_count": len(users)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@celery_app.task
def generate_payment_reports():
    """Generate automated payment reports"""
    db = SessionLocal()
    try:
        # Daily payment summary
        today = date.today()
        
        daily_payments = db.query(Payment).filter(
            Payment.payment_date == today,
            Payment.status == "confirmed"
        ).all()
        
        total_amount = sum(float(payment.amount) for payment in daily_payments)
        
        # Send summary to admin
        from app.models.user import User
        from app.core.permissions import UserRole
        
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        
        summary_message = f"""Daily Payment Summary - {today.strftime('%Y-%m-%d')}
Total Payments: {len(daily_payments)}
Total Amount: KES {total_amount:,.2f}

M-Pesa: {len([p for p in daily_payments if p.payment_method == 'mpesa'])}
Manual: {len([p for p in daily_payments if p.payment_method == 'cash'])}
Auto: {len([p for p in daily_payments if p.payment_method == 'drawdown_auto'])}

- Kim Loans System"""
        
        for admin in admins:
            send_notification_async.delay(
                admin.id,
                "Daily Payment Summary",
                summary_message,
                "system"
            )
        
    except Exception as e:
        print(f"Error generating payment reports: {e}")
    finally:
        db.close()


# Task for loan disbursement notifications
@celery_app.task
def send_loan_approval_notification(loan_application_id: int):
    """Send loan approval notification"""
    db = SessionLocal()
    try:
        from app.models.loan import LoanApplication
        
        application = db.query(LoanApplication).filter(
            LoanApplication.id == loan_application_id
        ).first()
        
        if application and application.status == "approved":
            approval_message = SMSTemplates.loan_approved(
                application.applicant.first_name,
                application.total_amount,
                application.application_number
            )
            
            send_sms_async.delay(application.applicant.phone_number, approval_message)
            
            send_notification_async.delay(
                application.applicant_id,
                "Loan Approved!",
                f"Your loan application {application.application_number} has been approved for KES {application.total_amount:,.2f}",
                "approval"
            )
        
    except Exception as e:
        print(f"Error sending loan approval notification: {e}")
    finally:
        db.close()