import frappe
from frappe.utils import nowdate, flt
from erpnext.stock.get_item_details import get_item_details

def _get_patient_customer(patient: str) -> str:
    cust = frappe.db.get_value("Patient", patient, "customer")
    if not cust:
        frappe.throw("This Patient is not linked to a Customer.")
    return cust

def _resolve_price_list(customer: str | None) -> str | None:
    return (
        (frappe.db.get_value("Customer", customer, "default_price_list") if customer else None)
        or frappe.db.get_single_value("Selling Settings", "selling_price_list")
    )

def _income_account_for(item_code: str, company: str) -> str:
    acc = frappe.db.get_value("Item Default", {"parent": item_code, "company": company}, "income_account")
    if not acc:
        acc = frappe.get_cached_value("Company", company, "default_income_account")
    if not acc:
        frappe.throw("Set Income Account on Item Default or Company → Default Income Account.")
    return acc

def _uom_and_cf(item_doc) -> tuple[str, float]:
    uom = item_doc.get("sales_uom") or item_doc.stock_uom
    if uom == item_doc.stock_uom:
        return uom, 1.0
    cf = frappe.db.get_value("UOM Conversion Detail", {"parent": item_doc.name, "uom": uom}, "conversion_factor")
    return uom, flt(cf or 1.0)

def _copy_receipt_to(encounter_name: str, target_doctype: str, target_name: str, file_url: str | None):
    if not file_url:
        return
    file_row = frappe.db.get_value(
        "File",
        {"attached_to_doctype": "Patient Encounter", "attached_to_name": encounter_name, "file_url": file_url},
        ["name", "file_name", "is_private", "file_url"],
        as_dict=True,
    )
    if not file_row:
        return
    f = frappe.new_doc("File")
    f.file_url = file_row.file_url
    f.file_name = file_row.get("file_name")
    f.is_private = file_row.get("is_private") or 0
    f.attached_to_doctype = target_doctype
    f.attached_to_name = target_name
    f.insert(ignore_permissions=True)

@frappe.whitelist()
def make_draft_invoice_and_payments(encounter_name: str, cfg: dict):
    """Create DRAFT Sales Invoice + DRAFT Payment Entries from Patient Encounter."""
    enc = frappe.get_doc("Patient Encounter", encounter_name)
    customer = _get_patient_customer(enc.patient)

    items_table       = cfg.get("items_table")          # "draft_items"
    payments_table    = cfg.get("payments_table")       # "draft_payments"
    item_field        = cfg.get("item_field")           # "item"
    qty_field         = cfg.get("qty_field")            # "quantity"
    rate_field        = cfg.get("rate_field")           # "rate" (optional)
    amount_field      = cfg.get("amount_field")         # "amount" (optional)
    mop_field         = cfg.get("mop_field")            # "mode_of_payment"
    pay_amount_field  = cfg.get("pay_amount_field")     # "amount"
    receipt_field     = cfg.get("receipt_attach_field") # "payment_receipt"
    update_stock      = int(cfg.get("update_stock") or 0)
    warehouse         = cfg.get("warehouse")

    price_list = _resolve_price_list(customer)

    # Sales Invoice (DRAFT)
    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company = enc.company
    si.posting_date = nowdate()
    si.update_stock = 1 if update_stock else 0

    added_any = False
    for r in (enc.get(items_table) or []):
        item_code = r.get(item_field)
        if not item_code:
            continue
        qty = flt(r.get(qty_field) or 1)

        # Try ERPNext defaults
        d = {}
        try:
            args = frappe._dict({
                "doctype": "Sales Invoice",
                "company": enc.company,
                "customer": customer,
                "price_list": price_list,
                "plc_conversion_rate": 1,
                "item_code": item_code,
                "qty": qty,
                "transaction_date": nowdate(),
                "is_pos": 0,
            })
            d = get_item_details(args) or {}
        except Exception:
            d = {}

        # Guarantee mandatory fields
        item_doc = frappe.get_cached_doc("Item", item_code)
        uom, conv = _uom_and_cf(item_doc)
        income_acc = d.get("income_account") or _income_account_for(item_doc.name, enc.company)
        rate = flt(d.get("price_list_rate") or d.get("rate") or r.get(rate_field) or 0)

        row = {
            "item_code": item_doc.name,
            "item_name": d.get("item_name") or item_doc.item_name,
            "description": d.get("description") or item_doc.description or item_doc.item_name,
            "uom": d.get("uom") or uom,
            "conversion_factor": d.get("conversion_factor") or conv,
            "qty": qty,
            "rate": rate,
            "amount": qty * rate,
            "income_account": income_acc,
        }
        if warehouse:
            row["warehouse"] = warehouse
        elif d.get("warehouse"):
            row["warehouse"] = d.get("warehouse")
        if amount_field and flt(r.get(amount_field)):
            row["amount"] = flt(r.get(amount_field))

        si.append("items", row)
        added_any = True

    if not added_any:
        frappe.throw("No valid items in Draft Invoice tab.")

    si.run_method("set_missing_values")
    si.run_method("calculate_taxes_and_totals")
    si.insert(ignore_permissions=True)   # DRAFT

    # Payment Entries (DRAFT)
    pe_names = []
    receipt_url = enc.get(receipt_field)

    for p in (enc.get(payments_table) or []):
        amt = flt(p.get(pay_amount_field) or 0)
        if amt <= 0:
            continue
        mop = p.get(mop_field)
        if not mop:
            frappe.throw("Mode of Payment is required in each Draft Payment row.")

        pe = frappe.new_doc("Payment Entry")
        pe.company = enc.company
        pe.payment_type = "Receive"
        pe.posting_date = nowdate()
        pe.party_type = "Customer"
        pe.party = customer
        pe.mode_of_payment = mop
        pe.paid_amount = amt
        pe.received_amount = amt
        pe.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "allocated_amount": amt,
        })
        pe.insert(ignore_permissions=True)  # DRAFT
        pe_names.append(pe.name)
        _copy_receipt_to(encounter_name, "Payment Entry", pe.name, receipt_url)

    return {"sales_invoice": si.name, "payment_entries": pe_names}
