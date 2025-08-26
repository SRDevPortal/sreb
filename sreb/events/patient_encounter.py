# sreb/events/patient_encounter.py
import frappe
from sreb.api.encounter_billing import make_draft_invoice_and_payments

def auto_make_draft_billing(doc, method=None):
    """
    After Save: if Encounter Type = Order and items exist,
    create DRAFT Sales Invoice + DRAFT Payment Entry(ies).
    Never create duplicates, and never block saving if something fails.
    """
    try:
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

        res = make_draft_invoice_and_payments(doc.name, cfg) or {}
        si_name = res.get("sales_invoice")
        if si_name:
            frappe.db.set_value("Patient Encounter", doc.name,
                                "generated_sales_invoice", si_name, update_modified=False)
            doc.add_comment("Info", f"Draft Sales Invoice <b>{frappe.utils.escape_html(si_name)}</b> created automatically.")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "sreb auto_make_draft_billing")
        # Optional gentle notice in timeline (does not block save)
        try:
            doc.add_comment("Comment", "Auto-create of Draft Sales Invoice failed. See Error Log for details.")
        except Exception:
            pass
