"""
Hard Comparator - 精确执行关键字段的代码级硬比对
V3.0 - 负责姓名、账户、证件等不可由大模型主观猜测的刚性字段对比
"""
import re
from backend.models.schemas import EFlowData, DocExtractedData, CheckResult, Severity

def _clean_str(val: str) -> str:
    """清理字符串：大写、去空格、去特殊字符以便对齐比对"""
    if not val:
        return ""
    # 去除中间和两边的空格，统一转大写
    clean = re.sub(r'[\s\-:：_]', '', str(val)).upper()
    return clean

def _is_name_match(name1: str, name2: str) -> bool:
    if not name1 or not name2:
        return False
    c1 = _clean_str(name1)
    c2 = _clean_str(name2)
    # 允许包含关系 (例如 "Wang Wei" vs "WangWei(CEO)")
    return c1 in c2 or c2 in c1

def run_hard_comparisons(eflow: EFlowData, doc_ext: DocExtractedData) -> list[CheckResult]:
    """对单份文档提取的数据进行硬比对"""
    checks = []
    
    doc_type = doc_ext.source_type # "word" / "ocr" / "pdf"
    
    # 1. 对比公司信用代码
    if eflow.company.cert_number and doc_ext.company.cert_number:
        e_cmp = _clean_str(eflow.company.cert_number)
        d_cmp = _clean_str(doc_ext.company.cert_number)
        if e_cmp != d_cmp:
            checks.append(CheckResult(
                check_name="公司证件号精确比对",
                field_name="company_cert",
                source_a_label="EFlow", source_a_value=str(eflow.company.cert_number),
                source_b_label=f"提取-{doc_type}", source_b_value=str(doc_ext.company.cert_number),
                result="MISMATCH", severity=Severity.CRITICAL,
                detail=f"公司信用代码不一致"
            ))
        else:
            checks.append(CheckResult(
                check_name="公司证件号精确比对",
                field_name="company_cert",
                source_a_label="EFlow", source_a_value=str(eflow.company.cert_number),
                source_b_label=f"提取-{doc_type}", source_b_value=str(doc_ext.company.cert_number),
                result="MATCH", severity=Severity.PASS,
                detail="公司信用代码核对一致"
            ))

    # 2. 对于 OCR 提取的证件：重点在于核对人员信息是否属于 EFlow 的名单
    if doc_type == "ocr" and doc_ext.persons:
        # 构建 eflow 全量人员池（申请人 + 用户）
        eflow_names = []
        eflow_ids = []
        if eflow.applicant.name: eflow_names.append(eflow.applicant.name)
        if eflow.applicant.id_number: eflow_ids.append(eflow.applicant.id_number)
        
        for u in eflow.users:
            if u.user_name: eflow_names.append(u.user_name)
        
        for p in doc_ext.persons:
            # 查身份证号
            id_matched = False
            if p.id_number:
                p_id_clean = _clean_str(p.id_number)
                for eid in eflow_ids:
                    if _clean_str(eid) == p_id_clean:
                        id_matched = True
                        break
            
            # 查姓名
            name_matched = False
            if p.name:
                for ename in eflow_names:
                    if _is_name_match(p.name, ename):
                        name_matched = True
                        break
                        
            if not id_matched and not name_matched:
                if p.name or p.id_number:
                    checks.append(CheckResult(
                        check_name="证件实体收录核查",
                        field_name="person_whitelist",
                        source_a_label="EFlow配置名单", source_a_value=str(f"姓名池:{eflow_names}"),
                        source_b_label="OCR解析名字", source_b_value=str(p.name),
                        result="MISMATCH", severity=Severity.WARNING,
                        detail="发现不在 EFlow 审批名单内的持证人，请核实是否有未报备人员"
                    ))
            else:
                checks.append(CheckResult(
                    check_name="证件白名单归属",
                    field_name="person_whitelist",
                    source_a_label="EFlow白名单", source_a_value="系统名册",
                    source_b_label="OCR身份", source_b_value=str(p.name or p.id_number),
                    result="MATCH", severity=Severity.PASS,
                    detail=f"证件实体 ({p.name}) 在审批范畴内"
                ))
    
    # 3. 对于 Word/PDF 表单：提取的多个 users 与 eflow 的 users 对比
    if doc_type in ["word", "pdf"] and doc_ext.users:
        eflow_users = eflow.users
        for doc_u in doc_ext.users:
            # 根据 name 或 account 找匹配项
            matched_ef_u = None
            for ef_u in eflow_users:
                if doc_u.user_name and ef_u.user_name and _is_name_match(doc_u.user_name, ef_u.user_name):
                    matched_ef_u = ef_u
                    break
            
            # 如果名字对上，校验他们的账号
            if matched_ef_u and matched_ef_u.account_number and doc_u.account_number:
                ef_acc = _clean_str(matched_ef_u.account_number)
                doc_acc = _clean_str(doc_u.account_number)
                if ef_acc != doc_acc:
                     checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})账号绑定校验",
                        field_name="user_account",
                        source_a_label="EFlow下发", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="表单填写", source_b_value=str(doc_u.account_number),
                        result="MISMATCH", severity=Severity.CRITICAL,
                        detail="绑定账号与系统电子流账号打架，存在被篡改的重大合规风险"
                    ))
                else:
                    checks.append(CheckResult(
                        check_name=f"操作员({doc_u.user_name})账号绑定校验",
                        field_name="user_account",
                        source_a_label="EFlow下发", source_a_value=str(matched_ef_u.account_number),
                        source_b_label="表单填写", source_b_value=str(doc_u.account_number),
                        result="MATCH", severity=Severity.PASS,
                        detail="绑定账号精准一致"
                    ))

    return checks
