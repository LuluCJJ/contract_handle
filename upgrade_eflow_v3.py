import os
import json
from pathlib import Path

def upgrade_directory(data_dir: Path):
    for case_dir in data_dir.iterdir():
        if not case_dir.is_dir():
            continue
            
        eflow_path = case_dir / "eflow.json"
        
        # skip manually handled case_013 or already handled ones
        if case_dir.name == "case_013_icbc_cert_pass":
            continue
            
        if not eflow_path.exists():
            continue
            
        with open(eflow_path, "r", encoding="utf-8") as f:
            try:
                old = json.load(f)
            except:
                continue

        # Detect if it's already V3 (has 'users' key)
        if "users" in old and isinstance(old["users"], list):
            continue

        # --- Mapping Logic ---
        v3 = {
            "flow_id": old.get("flow_id", "EF2026_" + case_dir.name),
            "business_type": "开通" if "开" in old.get("activity", "") else old.get("activity", "变更"),
            "business_scenario": old.get("activity", ""),
            "platform": {
                "platform_code": "SYS_001",
                "platform_name": "对应网银平台",
                "bank_name": "中国银行" if "boc" in case_dir.name else 
                             ("建设银行" if "ccb" in case_dir.name else 
                             ("工商银行" if "icbc" in case_dir.name else "测试银行")),
                "bank_name_en": "BOC/CCB/ICBC",
                "country": "中国",
                "branch_name": "相关分行"
            },
            "company": old.get("company", {}),
            "applicant": {
                "name": "",
                "department": "通用申请部"
            },
            "users": []
        }

        # Handle operators
        ops = old.get("operator", [])
        if isinstance(ops, dict): ops = [ops]

        # Handle handlers (put into applicant usually)
        hds = old.get("handler", [])
        if isinstance(hds, dict): hds = [hds]
        if hds and hds[0].get("name"):
            v3["applicant"]["name"] = hds[0].get("name")
        elif ops and ops[0].get("name"):
            v3["applicant"]["name"] = ops[0].get("name") # Fallback

        accs = old.get("account", [])
        if isinstance(accs, dict): accs = [accs]
        acc_num = accs[0].get("account_number") if accs else ""

        perms = old.get("permissions", {})

        # Populate users based on old operators
        for i, op in enumerate(ops):
            nm = op.get("name", f"User_{i}")
            
            # Simple heuristic for permission scope based on old activity/perms level
            act = old.get("activity", "")
            scope = {
                "authorize": "A" in perms.get("level", "") or "授权" in act,
                "payment": True, # assume true for most test cases
                "query": True,
                "upload": "上载" in act or "C" in perms.get("level", "")
            }

            u = {
              "user_name": nm,
              "permission_sub_type": op.get("role", "Default User"),
              "permission_scope": scope,
              "media": {
                "existing_media": "",
                "media_type": "U盾/Token",
                "is_blank": False
              },
              "account_number": acc_num,
              "account_status": "In Use",
              "single_limit": perms.get("single_limit", 1000000),
              "daily_limit": perms.get("daily_limit", 5000000)
            }
            v3["users"].append(u)

        # Write back
        with open(eflow_path, "w", encoding="utf-8") as f:
            json.dump(v3, f, ensure_ascii=False, indent=2)
            
        print(f"Upgraded -> {case_dir.name}")

if __name__ == "__main__":
    upgrade_directory(Path("test_data"))
    print("V3 EFlow Upgrade Complete.")
