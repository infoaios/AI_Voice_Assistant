project_root/
├── main_websocket.py        # Application entry point (voice loop orchestration)
├── .env                     # Environment variables

├── core/                    # Core domain & deterministic logic
│   ├── __init__.py
│   ├── order_manager.py     # Order state, add/remove/update/finalize
│   ├── restaurant_rag.py    # RAG + intent handling (authoritative brain)
│   ├── intent_router.py     # Intent classification & confidence scoring
│   ├── response_templates.py# Fixed responses (no LLM)
│   ├── restaurant_data.py   # Menu & restaurant metadata loader
│   └── nlp_utils.py         # Pure text utilities (NO IO, NO audio)

├── utility/                 # Shared helpers (non-business)
│   └── voice_reference_utils.py
│       └── Audio trimming & preprocessing for voice cloning

├── websocket/               # Network / inference layer (stateless)
│   ├── __init__.py
│   ├── stt/
│   │   ├── __init__.py
│   │   └── stt_websocket.py # Whisper STT (audio → text)
│   ├── tts/
│   │   ├── __init__.py
│   │   └── tts_websocket.py # XTTS v2 (text → audio)
│   └── ttt/
│       ├── __init__.py
│       └── llm_websocket.py # TinyLlama / LLM (text → text)
