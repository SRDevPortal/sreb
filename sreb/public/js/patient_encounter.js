// sreb — Patient Encounter helpers (safe guards)

function isOrder(frm) {
  return (frm.doc.encounter_type || "") === "Order";
}

function safe_set_query(frm, fieldname, child_table, filtersObj) {
  try {
    // if child_table provided, ensure that table field exists on the form
    if (child_table && !frm.fields_dict[child_table]) return;
    // if link field isn't on the form (e.g., custom field missing), skip
    if (!child_table && !frm.fields_dict[fieldname]) return;

    // build dict filters (works with Healthcare overrides)
    const q = () => ({ filters: filtersObj || {} });
    child_table ? frm.set_query(fieldname, child_table, q) : frm.set_query(fieldname, q);
  } catch (e) {
    console.error("[sreb] set_query guard", fieldname, e);
  }
}

function safe_toggle(frm, fieldname, show) {
  try {
    if (frm.fields_dict[fieldname]) frm.toggle_display(fieldname, !!show);
  } catch (e) {
    console.error("[sreb] toggle guard", fieldname, e);
  }
}

frappe.ui.form.on("Patient Encounter", {
  setup(frm) {
    // Medication filters by Medication Class (only if those tables exist)
    safe_set_query(frm, "medication", "drug_prescription",            { medication_class: "Ayurvedic Medicine" });
    safe_set_query(frm, "medication", "homeopathy_drug_prescription", { medication_class: "Homeopathic Medicine" });
    safe_set_query(frm, "medication", "allopathy_drug_prescription",  { medication_class: "Allopathic Medicine" });

    // Practitioner filters by pathy (only if those link fields exist)
    safe_set_query(frm, "ayurvedic_practitioner",  null, { pathy: "Ayurveda",   status: "Active" });
    safe_set_query(frm, "homeopathy_practitioner", null, { pathy: "Homeopathy", status: "Active" });
    safe_set_query(frm, "allopathy_practitioner",  null, { pathy: "Allopathy",  status: "Active" });
  },

  onload(frm) {
    safe_toggle(frm, "draft_invoice", isOrder(frm));
  },

  encounter_type(frm) {
    safe_toggle(frm, "draft_invoice", isOrder(frm));
  },

  refresh(frm) {
    safe_toggle(frm, "draft_invoice", isOrder(frm));

    if (!frm.is_new() && isOrder(frm)) {
      // avoid double buttons on refresh
      if (!frm.custom_buttons_added) {
        frm.add_custom_button("Create Invoice & Payments", () => {
          frappe.prompt([
            { fieldname: "warehouse",     label: "Warehouse (optional)", fieldtype: "Link", options: "Warehouse" },
            { fieldname: "update_stock",  label: "Update Stock",         fieldtype: "Check", default: 0 },
            { fieldname: "use_price_list",label: "Auto Price from Price List", fieldtype: "Check", default: 1 }
          ], (v) => {
            frappe.call({
              method: "sreb.api.encounter_billing.make_invoice_and_payments_option_b",
              args: {
                encounter_name: frm.doc.name,
                cfg: {
                  items_table: "draft_items",
                  payments_table: "draft_payments",
                  item_field: "item",
                  qty_field: "qty",
                  rate_field: "rate",
                  mop_field: "mode_of_payment",
                  pay_amount_field: "amount",
                  receipt_attach_field: "payment_receipt",
                  update_stock: v.update_stock ? 1 : 0,
                  warehouse: v.warehouse || null
                }
              },
              freeze: true,
              callback: (r) => {
                if (!r.message) return;
                const msg = `Sales Invoice <b>${r.message.sales_invoice}</b> created`
                  + (Array.isArray(r.message.payment_entries) && r.message.payment_entries.length
                      ? ` with ${r.message.payment_entries.length} payment(s): <b>${r.message.payment_entries.join(", ")}</b>`
                      : "");
                frappe.msgprint(msg);
                frappe.set_route("Form", "Sales Invoice", r.message.sales_invoice);
              }
            });
          }, "Invoice Options");
        }, "Billing");
        frm.custom_buttons_added = true;
      }
    }
  }
});
