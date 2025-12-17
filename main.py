#!/usr/bin/env python3
"""
Voice Platform - Main Entry Point
Refactored from monolithic assistant_final.py
"""
import warnings
import torch

import sys
from pathlib import Path

# Add project root to path for imports
if __name__ == "__main__":
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Import from project root (all modules are in root-level directories)
from services.infrastructure.logger_service import setup_logging, log_conversation
from services.infrastructure.vad_service import VADService
from services.infrastructure.audio_processor import AudioProcessor
from services.business.entity_service import EntityService
from services.business.action_service import ActionService
from services.business.policy_service import PolicyService
from services.receptionist.dialog_manager import DialogManager
from services.flows.stt_flow import STTFlow
from services.flows.ttt_flow import TTTFlow
from services.flows.tts_flow import TTSFlow
from repos.json_repo import JSONRepository
from repos.entities.order_entity import OrderManager
from llms.STT.stt_service import STTService
from llms.TTT.ttt_service import TTTService
from llms.TTS.tts_service import TTSService

warnings.filterwarnings("ignore", category=UserWarning)

# Initialize logging
logger = setup_logging()


def main():
    """Main application entry point"""
    print("=" * 70)
    print("🍽️  RESTAURANT AI ASSISTANT - MODULAR VERSION")
    print("=" * 70)
    
    # Initialize repositories
    json_repo = JSONRepository()
    
    # Initialize services
    vad_service = VADService()
    audio_processor = AudioProcessor(vad_service)
    entity_service = EntityService(json_repo)
    action_service = ActionService()
    policy_service = PolicyService()
    # DialogManager now uses interfaces - can accept any implementation
    dialog_manager = DialogManager(
        menu_repo=json_repo,  # IMenuRepository
        entity_service=entity_service,  # IEntityService
        action_service=action_service,  # IActionService
        policy_service=policy_service  # IPolicyService
    )
    
    # Initialize LLM services
    stt_service = STTService()
    ttt_service = TTTService(json_repo)
    tts_service = TTSService()
    
    # Initialize flows
    stt_flow = STTFlow(stt_service, audio_processor)
    ttt_flow = TTTFlow(ttt_service, dialog_manager, policy_service)
    tts_flow = TTSFlow(tts_service)
    
    # Initialize order manager
    order = OrderManager()
    
    try:
        while True:
            # STT Flow
            result = stt_flow.process()
            if result is None:
                continue
            
            text, stt_time = result
            
            # TTT Flow (Dialog + LLM)
            reply, brain_time, json_used, llm_time = ttt_flow.process(text, order)
            
            # Log conversation
            log_conversation(text, reply, order.to_json(), logger)
            
            # TTS Flow
            tts_time = tts_flow.process(reply)
            
            # Summary
            total_time = stt_time + brain_time + tts_time
            print(f"\n[Latency Summary]")
            print(f"  STT: {stt_time:.2f}s | Brain: {brain_time:.2f}s (JSON={json_used}, LLM={llm_time:.2f}s) | TTS: {tts_time:.2f}s")
            print(f"  TOTAL: {total_time:.2f}s")
            print("-" * 70)
            
            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    except KeyboardInterrupt:
        print("\n\n[Exit] 👋 Thank you for using the restaurant assistant!")
        print(f"📊 Current order status: {len(order.lines)} items")
        if not order.is_empty():
            print("⚠️  You have unsaved items in your cart!")
        print("Goodbye!")


if __name__ == "__main__":
    main()

