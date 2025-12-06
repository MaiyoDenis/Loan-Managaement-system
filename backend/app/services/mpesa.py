"""
SMS Gateway Integration Service
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.config import settings
from app.models.loan import SMSLog
from app.database import SessionLocal


class SMSService:
    """SMS gateway service for notifications"""
    
    def __init__(self):
        self.api_key = settings.SMS_API_KEY
        self.username = settings.SMS_USERNAME
        self.api_url = settings.SMS_API_URL
    
    async def send_sms(self, phone_number: str, message: str, 
                      notification_id: Optional[int] = None) -> Dict[str, Any]:
        """Send SMS using Africa's Talking API"""
        try:
            # Prepare payload
            payload = {
                'username': self.username,
                'to': phone_number,
                'message': message,
                'from': 'KIMLOANS'  # Sender ID
            }
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'apiKey': self.api_key
            }
            
            # Send request
            response = requests.post(self.api_url, data=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # Parse response
            sms_data = result.get('SMSMessageData', {})
            recipients = sms_data.get('Recipients', [])
            
            success = False
            provider_response = str(result)
            
            if recipients:
                recipient_data = recipients[0]
                status_code = recipient_data.get('statusCode')
                success = status_code == 101  # 101 means success in Africa's Talking
                provider_response = recipient_data.get('status', str(result))
            
            # Log SMS in database
            await self._log_sms(
                phone_number=phone_number,
                message=message,
                status='sent' if success else 'failed',
                provider_response=provider_response,
                notification_id=notification_id
            )
            
            return {
                "success": success,
                "message": "SMS sent successfully" if success else "Failed to send SMS",
                "provider_response": provider_response,
                "cost": sms_data.get('cost', 'Unknown')
            }
            
        except Exception as e:
            # Log failed SMS
            await self._log_sms(
                phone_number=phone_number,
                message=message,
                status='failed',
                provider_response=str(e),
                notification_id=notification_id
            )
            
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send SMS"
            }
    
    async def send_bulk_sms(self, recipients: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send bulk SMS to multiple recipients"""
        results = []
        
        for recipient in recipients:
            phone_number = recipient.get('phone_number')
            message = recipient.get('message')
            notification_id = recipient.get('notification_id')
            
            if phone_number and message:
                result = await self.send_sms(phone_number, message, notification_id)
                results.append({
                    "phone_number": phone_number,
                    "success": result["success"],
                    "message": result["message"]
                })
        
        successful_sends = sum(1 for r in results if r["success"])
        
        return {
            "total_sent": len(results),
            "successful": successful_sends,
            "failed": len(results) - successful_sends,
            "results": results
        }
    
    async def _log_sms(self, phone_number: str, message: str, status: str,
                      provider_response: str, notification_id: Optional[int] = None):
        """Log SMS in database"""
        db = SessionLocal()
        try:
            sms_log = SMSLog(
                phone_number=phone_number,
                message=message,
                status=status,
                provider_response=provider_response,
                notification_id=notification_id
            )
            
            db.add(sms_log)
            db.commit()
            
        except Exception as e:
            print(f"Error logging SMS: {e}")
            db.rollback()
        finally:
            db.close()
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Kenya (+254)"""
        # Remove any spaces or special characters
        phone = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different formats
        if phone.startswith('254'):
            return f"+{phone}"
        elif phone.startswith('0'):
            return f"+254{phone[1:]}"
        elif len(phone) == 9:
            return f"+254{phone}"
        else:
            return f"+254{phone}"


# SMS Templates
class SMSTemplates:
    """Predefined SMS message templates"""
    
    @staticmethod
    def welcome_message(first_name: str, username: str, password: str, account_number: str) -> str:
        return f"""Welcome to Kim Loans, {first_name}! 
Your account has been created successfully.

Login Details:
Username: {username}
Password: {password}
Account Number: {account_number}

Please change your password after first login.
For support, call 0700000000"""
    
    @staticmethod
    def payment_confirmation(first_name: str, amount: Decimal, loan_number: str, 
                           balance: Decimal, next_payment_date: str) -> str:
        return f"""Dear {first_name},
Payment of KES {amount:,.2f} received for loan {loan_number}.

Remaining Balance: KES {balance:,.2f}
Next Payment Due: {next_payment_date}

Thank you for your payment!
- Kim Loans"""
    
    @staticmethod
    def payment_reminder(first_name: str, amount: Decimal, loan_number: str, 
                        due_date: str, days_remaining: int) -> str:
        return f"""Dear {first_name},
Reminder: Your loan payment is due soon.

Loan: {loan_number}
Amount Due: KES {amount:,.2f}
Due Date: {due_date}
Days Remaining: {days_remaining}

Pay via M-Pesa Paybill: {settings.MPESA_SHORTCODE}
Account: Your unique account number

- Kim Loans"""
    
    @staticmethod
    def arrears_notice(first_name: str, amount: Decimal, loan_number: str, 
                      days_overdue: int) -> str:
        return f"""Dear {first_name},
Your loan payment is overdue.

Loan: {loan_number}
Overdue Amount: KES {amount:,.2f}
Days Overdue: {days_overdue}

Please make payment immediately to avoid additional charges.
Contact your loan officer for assistance.

- Kim Loans"""
    
    @staticmethod
    def loan_approved(first_name: str, amount: Decimal, loan_number: str) -> str:
        return f"""Congratulations {first_name}!
Your loan application has been approved.

Loan Number: {loan_number}
Amount: KES {amount:,.2f}

Products will be disbursed within 24 hours.
- Kim Loans"""
    
    @staticmethod
    def registration_complete(first_name: str, account_number: str, loan_limit: Decimal) -> str:
        return f"""Welcome {first_name}!
Your registration is now complete.

Account: {account_number}
Loan Limit: KES {loan_limit:,.2f}

You can now apply for loans.
- Kim Loans"""


# Initialize SMS service
sms_service = SMSService()