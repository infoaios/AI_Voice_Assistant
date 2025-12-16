"""Text-to-Text service using TinyLlama"""
import time
import torch
import re
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import Tuple

from services.infrastructure.config_service import LLM_MODEL, LLM_DEVICE
from repos.json_repo import JSONRepository


class TTTService:
    """Text-to-Text service using TinyLlama LLM"""
    
    def __init__(self, json_repo: JSONRepository):
        self.device = LLM_DEVICE
        
        # GPU ONLY - no CPU fallback
        if self.device != "cuda":
            raise SystemExit(
                "[LLM] ERROR: GPU is required. This application does not support CPU mode.\n"
                "Please ensure GPU and cuDNN are properly installed."
            )
        
        self.memory = []
        self.first_greeting = True
        self.json_repo = json_repo

        print(f"[LLM] Loading TinyLlama on GPU...")
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                LLM_MODEL,
                torch_dtype=torch.float16,  # GPU only - always use float16
            ).to(self.device)
        except Exception as e:
            error_str = str(e).lower()
            is_cudnn_error = (
                "cudnn" in error_str or 
                ("cuda" in error_str and "dll" in error_str) or
                "cudnncreate" in error_str or
                "cudnn_ops" in error_str or
                "invalid handle" in error_str
            )
            
            if is_cudnn_error:
                raise SystemExit(
                    f"[LLM] ERROR: CUDA/cuDNN error detected: {e}\n"
                    "This application requires GPU with cuDNN support.\n\n"
                    "To fix:\n"
                    "  1. Install cuDNN: conda install -c conda-forge cudnn\n"
                    "  2. Or download from: https://developer.nvidia.com/cudnn\n"
                    "  3. Restart the application\n\n"
                    "Application will not run without GPU + cuDNN."
                ) from e
            else:
                raise SystemExit(
                    f"[LLM] ERROR: Failed to load LLM model on GPU: {e}\n"
                    "This application requires GPU. Please check your GPU setup."
                ) from e
        
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def system_prompt(self) -> str:
        return (
            "You are AI Voice assistant, a friendly restaurant receptionist. "
            "Speak ONLY in English. Keep responses very short (1 sentence max). "
            "Be warm, confident, helpful but always professional. "
            
            "CRITICAL RULES - YOU MUST FOLLOW THESE: "
            "1. NEVER describe how to make any food, dish, or beverage "
            "2. NEVER list ingredients, recipes, or cooking methods "
            "3. NEVER invent, create, or make up ANY dish names - whether real or fake "
            "4. NEVER describe dishes that are available in our menu - let the system handle that "
            "5. NEVER describe dishes that are NOT available in our menu "
            "6. NEVER include labels like 'System:', 'User:', 'Assistant:', or any text in brackets "
            "7. NEVER make up information about dishes like 'Gold Pocket', 'Indonesian dessert', or similar fake items "
            "8. NEVER suggest menu items or create options for the user "
            "9. If asked about ANY food, dishes, ingredients, recipes, or prices, ONLY say: 'Let me check that for you' "
            "10. If asked how to make something, say: 'Sorry, I don't have recipe information' "
            
            "Your role is ONLY for: "
            "- Greetings (Hello, Welcome) "
            "- Confirmations (Yes, Okay, Sure) "
            "- General conversation (How are you, Thank you) "
            "- Asking user to repeat unclear words "
            "- Ending conversations politely "
            
            "ALL food, menu, price, and order information is handled by an external system, NOT by you. "
            "If the user asks about food, dishes, recipes, ingredients, prices, or the menu, "
            "you MUST respond with exactly: 'Let me check that for you' "
            "Do NOT guess, do NOT invent, do NOT describe any food items under any circumstances."
        )
    
    def chat(self, user_text: str) -> Tuple[str, float]:
        """Generate LLM response"""
        self.memory.append(user_text)
        if len(self.memory) > 5:
            self.memory.pop(0)
        
        conversation = "\n".join(f"User: {m}" for m in self.memory)
        prompt = self.system_prompt() + "\n\nConversation:\n" + conversation + "\nAssistant:"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True).to(self.device)
        
        llm_start = time.time()
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=60,
                temperature=0.7,
                top_p=0.9,
                no_repeat_ngram_size=3,
                repetition_penalty=1.2,
            )
        elapsed = time.time() - llm_start
        
        generated = outputs[0][inputs["input_ids"].shape[-1]:]
        raw = self.tokenizer.decode(generated, skip_special_tokens=True).strip()
        cleaned = self.clean_english_reply(raw)
        
        # Inject restaurant greeting on first message
        if self.first_greeting:
            rest = self.json_repo.get_restaurant_info()
            name = rest.get("name", "our restaurant")
            addr = rest.get("address", "our location")
            
            cleaned = f"Welcome to {name}! We are located at {addr}. {cleaned}"
            self.first_greeting = False

        if not cleaned:
            cleaned = "How can I help you today?"
        
        print(f"[Timing] LLM: {elapsed:.2f}s")
        return cleaned, elapsed
    
    @staticmethod
    def clean_english_reply(raw: str) -> str:
        """Clean LLM output - ENHANCED VERSION"""
        if not raw:
            return ""
        
        raw = raw.replace("\n", " ").strip()
        
        # Remove common system artifacts
        banned_patterns = [
            r'system\s*response:',
            r'system:',
            r'user:',
            r'assistant:',
            r'\[assistant name\]',
            r'\[.*?\]',  # Remove anything in brackets
        ]
        
        for pattern in banned_patterns:
            raw = re.sub(pattern, '', raw, flags=re.IGNORECASE)
        
        # Split by punctuation
        parts = [p.strip() for p in raw.replace("?", ".").replace("!", ".").split(".") if p.strip()]
        
        cleaned_sentences = []
        
        for s in parts:
            # Skip if contains colon in first word (likely a label)
            if ":" in s.split(" ")[0]:
                continue
            cleaned_sentences.append(s)
        
        if not cleaned_sentences:
            return "How can I help you?"
        
        # Take only first 2 sentences
        cleaned = ". ".join(cleaned_sentences[:2])
        cleaned = cleaned.encode("ascii", "ignore").decode("ascii").strip()
        
        if cleaned and not cleaned.endswith((".", "?", "!")):
            cleaned += "."
        
        return cleaned

