import frappe
from frappe.utils import nowdate, flt
from erpnext.stock.get_item_details import get_item_details

def _get_patient_customer(patient: str) -> str:
    cust = frappe.db.get_value("Patient", patient, "customer")
    if not cust:
        frappe.throw("This Patient is not linked to a Customer. Link or auto-create a Customer on the Patient.")
    return cust

def _default_income_account(company: str) -> str | None:
    return frappe.get_cached_value("Company", company, "default_income_account")

def _resolve_price_list(customer: str | None) -> str | None:
    return (
        (frappe.db.get_value("Customer", customer, "default_price_list") if customer else None)
        or frappe.db.get_single_value("Selling Settings", "selling_price_list")
    )

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
    newf = frappe.new_doc("File")
    newf.file_url = file_row.file_url
    newf.file_name = file_row.get("file_name")
    newf.is_private = file_row.get("is_private") or 0
    newf.attached_to_doctype = target_doctype
    newf.attached_to_name = target_name
    newf.insert(ignore_permissions=True)

@frappe.whitelist()
def make_invoice_and_payments_option_b(encounter_name: str, cfg: dict):
    """Create Sales Invoice (and allocate payments) from Patient Encounter using get_item_details."""
    enc = frappe.get_doc("Patient Encounter", encounter_name)
    customer = _get_patient_customer(enc.patient)

    items_table       = cfg.get("items_table")
    payments_table    = cfg.get("payments_table")
    item_field        = cfg.get("item_field")
    qty_field         = cfg.get("qty_field")
    rate_field        = cfg.get("rate_field")      # fallback only
    amount_field      = cfg.get("amount_field")    # optional
    mop_field         = cfg.get("mop_field")
    pay_amount_field  = cfg.get("pay_amount_field")
    receipt_field     = cfg.get("receipt_attach_field")
    update_stock      = int(cfg.get("update_stock") or 0)
    warehouse         = cfg.get("warehouse")

    price_list = _resolve_price_list(customer)
    company_currency = frappe.get_cached_value("Company", enc.company, "default_currency")

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

        args = frappe._dict({
            "doctype": "Sales Invoice",
            "company": enc.company,
            "customer": customer,
            "currency": company_currency,
            "price_list": price_list,
            "plc_conversion_rate": 1,
            "item_code": item_code,
            "qty": qty,
            "transaction_date": nowdate(),
            "is_pos": 0,
        })
        d = get_item_details(args)

        rate = flt(d.get("price_list_rate") or d.get("rate") or r.get(rate_field) or 0)
        row = {
            "item_code": item_code,
            "item_name": d.get("item_name"),
            "description": d.get("description"),
            "uom": d.get("uom"),
            "conversion_factor": d.get("conversion_factor") or 1,
            "qty": qty,
            "rate": rate,
            "income_account": d.get("income_account") or _default_income_account(enc.company),
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
    si.insert(ignore_permissions=True)
    si.submit()

    payment_names = []
    receipt_url = enc.get(receipt_field)

    for p in (enc.get(payments_table) or []):
        amt = flt(p.get(pay_amount_field) or 0)
        if amt <= 0:
            continue
        mop = p.get(mop_field)
        if not mop:
            frappe.throw("Mode of Payment is required for each payment row.")

        pe = frappe.new_doc("Payment Entry")
        pe.company = enc.company
        pe.payment_type = "Receive"
        pe.posting_date = nowdate()
        pe.party_type = "Customer"
        pe.party = customer
        pe.mode_of_payment = mop
        pe.paid_amount = amt
        pe.received_amount = amt
        pe.references = [{
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
            "allocated_amount": amt,
        }]
        pe.insert(ignore_permissions=True)
        pe.submit()
        payment_names.append(pe.name)
        _copy_receipt_to(encounter_name, "Payment Entry", pe.name, receipt_url)

    return {"sales_invoice": si.name, "payment_entries": payment_names}
