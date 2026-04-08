import sys
import re

def _parse_id_card(all_text: list) -> dict:
    full_t = " ".join(all_text)
    name, id_n = "", ""
    if any(k in full_t for k in ["姓名", "身份", "公民"]):
        for i, t in enumerate(all_text):
            if "姓名" in t:
                name = t.replace("姓名", "").strip() or (all_text[i+1] if i+1 < len(all_text) else "")
                break
        for t in all_text:
            m = re.search(r'\d{17}[\dXx]', t)
            if m: id_n = m.group(); break
        if id_n: return {"name": name, "id_number": id_n, "id_type": "id_card"}
    return {}

def _parse_mrz(all_text: list) -> dict:
    full_t = "".join(all_text).upper()
    if "P<" in full_t or any(k in full_t for k in ["PASSPORT", "DOCNO", "DOCUMENT NO"]):
        for t in all_text:
            t = t.upper().replace(" ", "")
            m = re.search(r'[A-Z0-9]{9}\d[A-Z]{3}\d{6}', t)
            if m:
                pass_num = t[:9]
                return {"name": "Extracted via MRZ", "id_number": pass_num, "id_type": "passport"}
            m_simple = re.search(r'[A-Z]\d{8}|[A-Z0-9]{7,10}', t)
            if ("PASSPORT" in full_t or "DOC" in full_t) and m_simple:
                return {"name": "", "id_number": m_simple.group(), "id_type": "passport"}
    return {}

def test_passport_logic():
    print("--- V20.3 STANDALONE Passport/ID Logic Test ---")
    
    # CASE 1: Standard ID Card
    id_text = ["姓名: 张三", "性别: 男", "公民身份号码: 110101199001011234"]
    res_id = _parse_id_card(id_text)
    if res_id.get("id_type") == "id_card" and res_id.get("id_number") == "110101199001011234":
        print("[PASS] ID Card Path (Regex)")
    else:
        print(f"[FAIL] ID Card Path - Got: {res_id}")

    # CASE 2: International Passport (MRZ Line 2)
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
