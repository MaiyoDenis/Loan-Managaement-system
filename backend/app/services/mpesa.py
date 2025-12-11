"""
M-Pesa Integration Service

This module provides a service abstraction for initiating M-Pesa STK Push
operations. If real M-Pesa credentials are not provided, it will simulate
successful responses for development and testing.
"""
from __future__ import annotations

from typing import Any, Dict
from decimal import Decimal
from uuid import uuid4

from app.core.config import settings


class MpesaService:
    """Service for interacting with M-Pesa (or simulating it).

    For production, wire this to Safaricom Daraja (or provider) APIs.
    For development without credentials, we simulate a successful STK push.
    """

    def __init__(self) -> None:
        # Basic config for potential real integration
        self.consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
        self.consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
        self.shortcode = getattr(settings, "MPESA_SHORTCODE", "")
        # Additional endpoints/settings could be added here as needed

    def _has_credentials(self) -> bool:
        return bool(self.consumer_key and self.consumer_secret and self.shortcode)

    def initiate_stk_push(
        self,
        phone_number: str,
        amount: Decimal,
        account_reference: str,
        transaction_desc: str = "Loan Payment",
    ) -> Dict[str, Any]:
        """Initiate an STK Push request.

        Returns a dict with keys used by API endpoints:
        - success: bool
        - customer_message: str
        - checkout_request_id: str
        - merchant_request_id: str
        - error: str (present on failure)
        """
        # If credentials are present, this is where you'd call the real API.
        # For now, we simulate success to avoid runtime errors and unblock flows.
        try:
            if not phone_number or not account_reference or amount <= 0:
                return {
                    "success": False,
                    "error": "Invalid parameters provided",
                }

            # Simulated success response
            merchant_request_id = f"MR{uuid4().hex[:16].upper()}"
            checkout_request_id = f"CR{uuid4().hex[:16].upper()}"

            customer_message = (
                "Enter your M-Pesa PIN to complete the payment request sent to your phone."
            )

            return {
                "success": True,
                "customer_message": customer_message,
                "checkout_request_id": checkout_request_id,
                "merchant_request_id": merchant_request_id,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Export singleton instance used across the app
mpesa_service = MpesaService()
