import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from backend.services.ocr_service import _parse_id_card, _parse_mrz, extract_id_info

def test_passport_logic():
    print("--- V20.3 Passport/ID Dual-path Logic Test ---")
    
    # CASE 1: Standard ID Card
    id_text = ["姓名: 张三", "性别: 男", "公民身份号码: 110101199001011234"]
    res_id = _parse_id_card(id_text)
    if res_id.get("id_type") == "id_card" and res_id.get("id_number") == "110101199001011234":
        print("[PASS] ID Card Path (Regex)")
    else:
        print(f"[FAIL] ID Card Path - Got: {res_id}")

    # CASE 2: International Passport (MRZ Line 2)
    # Typical MRZ Line 2 for TD3: G12345678<8CHN9001014M2501013<<<<<<<<<<<<<<02
    passport_text = ["PASSPORT", "P<CHNLING<<ZHANG<<<<<<<<<<<<<<<<<<<<<<<<<<<<", "G123456788CHN9001014M2501013<<<<<<<<<<<<<<02"]
    res_pass = _parse_mrz(passport_text)
    if res_pass.get("id_type") == "passport" and res_pass.get("id_number") == "G12345678":
        print("[PASS] Passport Path (MRZ Parsing)")
    else:
        print(f"[FAIL] Passport Path - Got: {res_pass}")

    # CASE 3: Simple Passport (Keywords + Alphanumeric)
    pass_simple = ["DOCUMENT NO: AB1234567", "NAME: JOHN DOE", "PASSPORT"]
    res_simple = _parse_mrz(pass_simple)
    if res_simple.get("id_type") == "passport" and res_simple.get("id_number") == "AB1234567":
        print("[PASS] Passport Path (Keyword + Regex)")
    else:
        print(f"[FAIL] Passport Path (Simple) - Got: {res_simple}")

if __name__ == "__main__":
    test_passport_logic()
