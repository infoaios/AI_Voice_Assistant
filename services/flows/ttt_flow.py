"""
TTT Flow - orchestrates text-to-text (LLM) processing

Uses interfaces to reduce coupling between flows and services.
"""
# Use interfaces for stable contracts
try:
    from core.interfaces import ITTTService, IDialogService, IPolicyService, IOrderManager
except ImportError:
    # Fallback for backward compatibility
    from llms.TTT.ttt_service import TTTService as ITTTService
    from services.receptionist.dialog_manager import DialogManager as IDialogService
    from services.business.policy_service import PolicyService as IPolicyService
    from repos.entities.order_entity import OrderManager as IOrderManager


class TTTFlow:
    """
    Flow for Text-to-Text (LLM) processing
    
    Depends on service interfaces, allowing implementations to change.
    """
    
    def __init__(
        self,
        ttt_service: ITTTService,
        dialog_service: IDialogService,
        policy_service: IPolicyService
    ):
        """
        Initialize TTT flow with service interfaces
        
        Args:
            ttt_service: Text-to-text service interface
            dialog_service: Dialog service interface
            policy_service: Policy service interface
        """
        self.ttt_service = ttt_service
        self.dialog_service = dialog_service
        self.policy_service = policy_service
    
    def process(self, text: str, order: IOrderManager):
        """Process text and return response"""
        import time
        
        brain_start = time.time()
        
        # Try dialog service first (JSON-based responses)
        reply = self.dialog_service.process_message(text, order)
        json_used = reply is not None
        llm_time = 0.0
        
        if not reply:
            # CHECK if query should go to LLM
            if self.policy_service.should_block_llm(text):
                # Default response for food queries that JSON couldn't handle
                reply = "Let me check our menu for you. Could you please repeat the dish name clearly?"
            else:
                # Only non-food queries go to LLM
                reply, llm_time = self.ttt_service.chat(text)
                reply = self.ttt_service.clean_english_reply(reply)
        
        brain_time = time.time() - brain_start
        
        print(f"[AI]: {reply}")
        
        return reply, brain_time, json_used, llm_time

