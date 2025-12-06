"""
M-Pesa Integration API endpoints
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

from app.database import get_db
from app.models.loan import MpesaTransaction, Payment, Loan
from app.models.user import User
from app.services.mpesa import mpesa_service
from app.services.sms import sms_service, SMSTemplates
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.post("/stk-push")
async def initiate_payment(
    phone_number: str,
    amount: Decimal,
    account_reference: str,
    description: str = "Loan Payment",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Initiate STK Push payment"""
    
    # Find customer by account number
    customer = db.query(User).filter(
        User.unique_account_number == account_reference
    ).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer account not found"
        )
    
    # Format phone number
    formatted_phone = sms_service.format_phone_number(phone_number)
    
    # Initiate M-Pesa STK Push
    result = mpesa_service.initiate_stk_push(
        phone_number=formatted_phone,
        amount=amount,
        account_reference=account_reference,
        transaction_desc=description
    )
    
    if result["success"]:
        # Store pending transaction
        pending_transaction = MpesaTransaction(
            checkout_request_id=result["checkout_request_id"],
            merchant_request_id=result["merchant_request_id"],
            phone_number=formatted_phone,
            account_number=account_reference,
            amount=amount,
            transaction_time=datetime.utcnow(),
            status="pending",
            initiated_by=current_user.id
        )
        
        db.add(pending_transaction)
        db.commit()
        
        return {
            "success": True,
            "message": result["customer_message"],
            "checkout_request_id": result["checkout_request_id"],
            "amount": float(amount),
            "phone_number": formatted_phone
        }
    else:
        return {
            "success": False,
            "error": result["error"],
            "message": "Failed to initiate payment"
        }


@router.post("/confirmation")
async def mpesa_confirmation(request: Request, db: Session = Depends(get_db)) -> Any:
    """Handle M-Pesa payment confirmation callback"""
    try:
        # Parse callback data
        callback_data = await request.json()
        
        # Extract transaction details
        trans_id = callback_data.get('TransID')
        trans_time = callback_data.get('TransTime')
        trans_amount = Decimal(str(callback_data.get('TransAmount', 0)))
        bill_ref_number = callback_data.get('BillRefNumber')  # Customer account number
        phone_number = callback_data.get('MSISDN')
        first_name = callback_data.get('FirstName', '')
        last_name = callback_data.get('LastName', '')
        
        # Find customer by account number
        customer = db.query(User).filter(
            User.unique_account_number == bill_ref_number
        ).first()
        
        if not customer:
            return {"ResultCode": 1, "ResultDesc": "Invalid account number"}
        
        # Create M-Pesa transaction record
        mpesa_transaction = MpesaTransaction(
            transaction_code=trans_id,
            phone_number=phone_number,
            account_number=bill_ref_number,
            amount=trans_amount,
            transaction_time=datetime.strptime(trans_time, '%Y%m%d%H%M%S'),
            first_name=first_name,
            last_name=last_name,
            status="confirmed",
            processed=False
        )
        
        db.add(mpesa_transaction)
        db.commit()
        
        # Process payment asynchronously
        from app.tasks.payment_tasks import process_mpesa_payment_async
        process_mpesa_payment_async.delay(mpesa_transaction.id)
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        print(f"M-Pesa confirmation error: {e}")
        return {"ResultCode": 1, "ResultDesc": "Internal server error"}


@router.post("/validation")
async def mpesa_validation(request: Request, db: Session = Depends(get_db)) -> Any:
    """Handle M-Pesa payment validation callback"""
    try:
        # Parse validation data
        validation_data = await request.json()
        
        # Extract details
        bill_ref_number = validation_data.get('BillRefNumber')
        trans_amount = Decimal(str(validation_data.get('TransAmount', 0)))
        
        # Find customer by account number
        customer = db.query(User).filter(
            User.unique_account_number == bill_ref_number
        ).first()
        
        if not customer:
            return {
                "ResultCode": "C2B00011",
                "ResultDesc": "Invalid account number"
            }
        
        # Validate minimum amount (optional)
        if trans_amount < Decimal('1.00'):
            return {
                "ResultCode": "C2B00012",
                "ResultDesc": "Amount too small"
            }
        
        # Accept the transaction
        return {
            "ResultCode": "0",
            "ResultDesc": "Success"
        }
        
    except Exception as e:
        print(f"M-Pesa validation error: {e}")
        return {
            "ResultCode": "C2B00013",
            "ResultDesc": "Internal server error"
        }


@router.post("/callback")
async def stk_push_callback(request: Request, db: Session = Depends(get_db)) -> Any:
    """Handle STK Push callback"""
    try:
        callback_data = await request.json()
        
        # Extract callback details
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        # Find pending transaction
        mpesa_transaction = db.query(MpesaTransaction).filter(
            MpesaTransaction.checkout_request_id == checkout_request_id
        ).first()
        
        if mpesa_transaction:
            if result_code == 0:  # Success
                # Extract metadata
                callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                
                for item in callback_metadata:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_transaction.transaction_code = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        trans_date = str(item.get('Value'))
                        mpesa_transaction.transaction_time = datetime.strptime(trans_date, '%Y%m%d%H%M%S')
                
                mpesa_transaction.status = "confirmed"
                
                # Process payment
                from app.tasks.payment_tasks import process_mpesa_payment_async
                process_mpesa_payment_async.delay(mpesa_transaction.id)
                
            else:  # Failed
                mpesa_transaction.status = "failed"
                mpesa_transaction.failure_reason = result_desc
            
            db.commit()
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        print(f"STK Push callback error: {e}")
        return {"ResultCode": 1, "ResultDesc": "Internal server error"}


@router.get("/transactions")
def get_mpesa_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("payments:view_history")),
    skip: int = 0,
    limit: int = 100
) -> Any:
    """Get M-Pesa transaction history"""
    query = db.query(MpesaTransaction)
    
    # Apply branch filtering for non-admin users
    if current_user.role != "admin":
        # Get customers from current user's branch
        branch_customers = db.query(User).filter(
            User.branch_id == current_user.branch_id,
            User.role == "customer"
        ).all()
        
        account_numbers = [customer.unique_account_number for customer in branch_customers if customer.unique_account_number]
        query = query.filter(MpesaTransaction.account_number.in_(account_numbers))
    
    transactions = query.order_by(MpesaTransaction.created_at.desc()).offset(skip).limit(limit).all()
    
    return transactions


@router.post("/simulate-payment")
async def simulate_mpesa_payment(
    phone_number: str,
    amount: Decimal,
    account_reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("admin:system_settings"))
) -> Any:
    """Simulate M-Pesa payment for testing (Admin only)"""
    
    # Format phone number
    formatted_phone = sms_service.format_phone_number(phone_number)
    
    # Create simulated transaction
    mpesa_transaction = MpesaTransaction(
        transaction_code=f"SIM{datetime.now().strftime('%Y%m%d%H%M%S')}",
        phone_number=formatted_phone,
        account_number=account_reference,
        amount=amount,
        transaction_time=datetime.utcnow(),
        first_name="Test",
        last_name="User",
        status="confirmed",
        processed=False,
        is_simulation=True
    )
    
    db.add(mpesa_transaction)
    db.commit()
    db.refresh(mpesa_transaction)
    
    # Process payment
    from app.tasks.payment_tasks import process_mpesa_payment_async
    process_mpesa_payment_async.delay(mpesa_transaction.id)
    
    return {
        "success": True,
        "message": "Payment simulation initiated",
        "transaction_id": mpesa_transaction.id,
        "amount": float(amount)
    }