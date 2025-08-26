import frappe
from sreb.api.encounter_billing import make_draft_invoice_and_payments

def auto_make_draft_billing(doc, method=None):
    # Only for Order encounters; only once; only if items exist
    if (doc.encounter_type or "") != "Order":
        return
    if doc.get("generated_sales_invoice"):
        return
    if not (doc.get("draft_items") or []):
        return

    cfg = {
        "items_table": "draft_items",
        "payments_table": "draft_payments",
        "item_field": "item",
        "qty_field": "quantity",
        "rate_field": "rate",
        "mop_field": "mode_of_payment",
        "pay_amount_field": "amount",
        "receipt_attach_field": "payment_receipt",
        "update_stock": 0,
        "warehouse": None,
    }

    try:
        res = make_draft_invoice_and_payments(doc.name, cfg) or {}
        si_name = res.get("sales_invoice")
        if si_name:
            frappe.db.set_value("Patient Encounter", doc.name,
                                "generated_sales_invoice", si_name, update_modified=False)
            doc.add_comment("Info", f"Draft Sales Invoice <b>{si_name}</b> created automatically.")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "sreb auto_make_draft_billing")
