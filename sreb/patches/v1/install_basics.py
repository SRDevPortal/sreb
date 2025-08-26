import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    create_custom_fields({
        "Patient Encounter": [
            {"fieldname": "draft_invoice", "fieldtype": "Tab Break", "label": "Draft Invoice"},
            {"fieldname": "draft_items", "fieldtype": "Table", "label": "Item", "options": "Encounter Draft Item"},
            {"fieldname": "draft_payments", "fieldtype": "Table", "label": "Draft Payment", "options": "Encounter Draft Payment"},
            {"fieldname": "payment_receipt", "fieldtype": "Attach", "label": "Payment Receipt"},
            {"fieldname": "generated_sales_invoice", "fieldtype": "Link", "label": "Generated Sales Invoice",
             "options": "Sales Invoice", "read_only": 1},
        ]
    }, update=True)
