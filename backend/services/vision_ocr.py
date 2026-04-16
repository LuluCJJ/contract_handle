import os
import base64
from backend.services.llm_client import chat_vision_json
from backend.config import get_config

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_id_info_vision(image_path: str) -> dict:
    """
    Use standard LLM Vision capacities to extract ID card/Passport data.
    """
    if not os.path.exists(image_path):
        return {"name": "", "id_number": ""}
    
    cfg = get_config()
    system_prompt = cfg.get_prompt("id_extraction_fallback")
    if not system_prompt:
        system_prompt = "Extract info from image, return JSON only: name, id_number."

    try:
        base64_img = encode_image(image_path)
        print(f"[Vision OCR] Sending request for {image_path} via LLM Vision...")
        result = chat_vision_json(system_prompt, base64_img)
        
        # Normalize the result to ensure required keys exist
        return {
            "name": result.get("name", ""),
            "id_number": result.get("id_number", ""),
            "expiry_date": result.get("expiry_date", "")
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[Vision OCR] Error: {error_msg}")
        # Special handling for non-vision models (e.g. moonshot)
        if "Image input not supported" in error_msg or "400" in error_msg:
             print("[Vision OCR] Active model doesn't support Vision. Consider enabling local PaddleOCR or switching to GPT-4o/Claude-3.5-V.")
        return {"name": "", "id_number": "", "error": error_msg}
