"""
Action Service

Executes business actions such as order finalization, booking confirmations,
and other user-initiated operations. Links actions to REQUEST entities.

This service:
- Executes order finalization with customer details
- Extracts customer information (name, phone)
- Saves order data to persistence layer
- Returns action results and confirmation messages
"""
import time
import re
import json
import logging
from pathlib import Path
from typing import Tuple, Optional

from repos.entities.order_entity import OrderManager

logger = logging.getLogger(__name__)


class ActionService:
    """
    Service for executing business actions
    
    Handles order finalization and other user-initiated actions.
    Links to REQUEST entities in the system.
    """
    
    @staticmethod
    def finalize_order(order: OrderManager, text: str) -> Tuple[bool, Optional[str]]:
        """Finalize order with customer details"""
        text_low = text.lower()
        
        # Check for confirmation keywords
        confirm_keywords = ["confirm", "place order", "yes that's all", "proceed", "checkout", "finalize"]
        if not any(kw in text_low for kw in confirm_keywords):
            return False, None
        
        if order.is_empty():
            return True, "Your order is empty. Please add items first."
        
        # Extract name
        name = None
        if "my name is" in text_low:
            name = text_low.split("my name is")[1].split()[0].strip().title()
        elif "i am" in text_low or "i'm" in text_low:
            parts = text_low.replace("i'm", "i am").split("i am")
            if len(parts) > 1:
                name = parts[1].strip().split()[0].title()
        
        # Extract phone
        phone_match = re.search(r'\b\d{10}\b', text)
        phone = phone_match.group(0) if phone_match else None
        
        if name and phone:
            order_id = f"ORD{int(time.time())}"
            order_data = {
                "order_id": order_id,
                "customer_name": name,
                "phone": phone,
                "items": order.to_json()["items"],
                "total": order.subtotal(),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Save to file
            try:
                # Save to project root/orders directory
                # This file is in voice_platform/services/, so go up to voice_platform/, then to project root
                voice_platform_dir = Path(__file__).parent.parent  # voice_platform/
                project_root = voice_platform_dir.parent  # project root
                orders_dir = project_root / "orders"
                orders_dir.mkdir(exist_ok=True)
                with open(orders_dir / "orders_history.json", "a") as f:
                    f.write(json.dumps(order_data) + "\n")
                logger.info(f"Order saved: {order_id}")
            except Exception as e:
                logger.error(f"Could not save order: {e}")
            
            order.clear()
            return True, (
                f"Perfect! Your order {order_id} is confirmed for {name}. "
                f"We'll call you at {phone} when it's ready. Total: {order_data['total']:.0f} rupees. "
                f"Thank you!"
            )
        else:
            missing = []
            if not name:
                missing.append("name")
            if not phone:
                missing.append("phone number")
            return True, f"Please provide your {' and '.join(missing)} to confirm the order."

