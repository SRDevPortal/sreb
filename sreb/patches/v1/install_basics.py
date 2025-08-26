import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PRINT_FORMAT_NAME = "Patient Encounter Card"


def _ensure_print_format():
    """Create a minimal Patient Encounter print format if it doesn't exist."""
    if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        return

    html = """<style>
  .hdr-wrap { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111; font-size:10pt; margin-bottom:10pt; }
  .card    { width:100%; border:1.25pt solid #cfd6e4; border-collapse:collapse; table-layout:fixed; font-size:10pt; }
  .card td { vertical-align:top; padding:10px 0; font-size:10pt; }
  .card .left  { width:68%; padding: 0pt !important; }
  .card .right { width:32%; border-left:1.25pt solid #cfd6e4; padding: 0pt !important; }
  .kv            { width:100%; border-collapse:collapse; font-size:10pt; }
  .kv tr > td    { padding:3px 0; vertical-align:top; border-bottom:1px solid #e8ebf0; }
  .kv tr:last-child > td { border-bottom:0; }
  .lbl     { color:#444; width:120pt; white-space:nowrap; border-right:1px solid #e8ebf0; padding-right:0; background:#fafbfc; }
  .val     { padding-left:0; }
  .stack         { padding:0 !important; border-bottom:1px solid #e8ebf0; }
  .stack .title  { font-weight:600; color:#444; background:#fafbfc; padding:4px 0; }
  .stack .value  { padding:4px 0 8px 0; }
</style>

{% set patient = frappe.get_doc("Patient", doc.patient) if doc.patient else None %}
{% set patient_id    = doc.patient or (patient.name if patient else "") %}
{% set patient_name  = doc.patient_name or (patient.patient_name if patient else "") %}
{% set sex           = doc.sex or doc.patient_sex or (patient.sex if patient else "") %}
{% set age_text      = doc.patient_age or (patient.age if patient and patient.age else "") %}

<div class="hdr-wrap">
  <table class="card">
    <tr>
      <td class="left">
        <table class="kv">
          <tr><td class="lbl">Patient Name:</td><td class="val"><b>{{ patient_name }}</b></td></tr>
          <tr><td class="lbl">UHID / Patient ID:</td><td class="val">{{ patient_id }}</td></tr>
          {% if age_text or sex %}
          <tr><td class="lbl">Age / Sex:</td><td class="val">{{ (age_text ~ " ") if age_text else "" }}{{ sex }}</td></tr>
          {% endif %}
        </table>
      </td>
      <td class="right">
        <table class="kv">
          <tr><td colspan="2" class="stack">
            <div class="title">Encounter Date & Time</div>
            <div class="value">
              {% if doc.encounter_datetime %}
                {{ frappe.format(doc.encounter_datetime, {"fieldtype":"Datetime"}) }}
              {% elif doc.encounter_date %}
                {{ frappe.format(doc.encounter_date, {"fieldtype":"Date"}) }}
              {% else %}
                {{ frappe.format(doc.modified, {"fieldtype":"Datetime"}) }}
              {% endif %}
            </div>
          </td></tr>
          {% if doc.encounter_type %}
          <tr><td colspan="2" class="stack"><div class="title">Encounter Type</div><div class="value">{{ doc.encounter_type }}</div></td></tr>
          {% endif %}
        </table>
      </td>
    </tr>
  </table>
</div>"""

    pf = frappe.get_doc({
        "doctype": "Print Format",
        "name": PRINT_FORMAT_NAME,
        "doc_type": "Patient Encounter",
        "print_format_type": "Jinja",
        "html": html,
        "module": "Sreb",
    })
    pf.insert(ignore_permissions=True)


def execute():
    """Patch: create custom fields & minimal print format."""
    create_custom_fields({
        "Patient Encounter": [
            {"fieldname": "draft_invoice", "fieldtype": "Tab Break", "label": "Draft Invoice"},
            {"fieldname": "draft_items", "fieldtype": "Table", "label": "Item", "options": "Encounter Draft Item"},
            {"fieldname": "draft_payments", "fieldtype": "Table", "label": "Draft Payment", "options": "Encounter Draft Payment"},
            {"fieldname": "payment_receipt", "fieldtype": "Attach", "label": "Payment Receipt"},
            {"fieldname": "ayurvedic_practitioner", "fieldtype": "Link", "label": "Ayurvedic Practitioner", "options": "Healthcare Practitioner"},
            {"fieldname": "homeopathy_practitioner", "fieldtype": "Link", "label": "Homeopathy Practitioner", "options": "Healthcare Practitioner"},
            {"fieldname": "allopathy_practitioner", "fieldtype": "Link", "label": "Allopathy Practitioner", "options": "Healthcare Practitioner"},
        ]
    }, update=True)

    _ensure_print_format()
