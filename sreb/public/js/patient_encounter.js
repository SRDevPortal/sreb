\
    // sreb — Patient Encounter helpers
    function isOrder(frm) {
      return (frm.doc.encounter_type || "") === "Order";
    }

    frappe.ui.form.on("Patient Encounter", {
      setup(frm) {
        // Medication filters by Medication Class
        frm.set_query("medication", "drug_prescription",            () => ({ filters:{ medication_class:"Ayurvedic Medicine" }}));
        frm.set_query("medication", "homeopathy_drug_prescription", () => ({ filters:{ medication_class:"Homeopathic Medicine" }}));
        frm.set_query("medication", "allopathy_drug_prescription",  () => ({ filters:{ medication_class:"Allopathic Medicine" }}));

        // Practitioner filters by pathy
        frm.set_query("ayurvedic_practitioner",  () => ({ filters:{ pathy:"Ayurveda",   status:"Active" } }));
        frm.set_query("homeopathy_practitioner", () => ({ filters:{ pathy:"Homeopathy", status:"Active" } }));
        frm.set_query("allopathy_practitioner",  () => ({ filters:{ pathy:"Allopathy",  status:"Active" } }));
      },

      onload(frm) {
        frm.toggle_display("draft_invoice", isOrder(frm));
      },

      encounter_type(frm) {
        frm.toggle_display("draft_invoice", isOrder(frm));
      },

      refresh(frm) {
        frm.toggle_display("draft_invoice", isOrder(frm));

        if (!frm.is_new() && isOrder(frm)) {
          frm.add_custom_button("Create Invoice & Payments", () => {
            frappe.prompt([
              { fieldname:"warehouse", label:"Warehouse (optional)", fieldtype:"Link", options:"Warehouse" },
              { fieldname:"update_stock", label:"Update Stock", fieldtype:"Check", default:0 },
              { fieldname:"use_price_list", label:"Auto Price from Price List", fieldtype:"Check", default:1 }
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
                  const { sales_invoice, payment_entries } = r.message;
                  let msg = `Sales Invoice <b>${sales_invoice}</b> created`;
                  if (payment_entries?.length) msg += ` with ${payment_entries.length} payment(s): <b>${payment_entries.join(", ")}</b>`;
                  frappe.msgprint(msg);
                  frappe.set_route("Form", "Sales Invoice", sales_invoice);
                }
              });
            }, "Invoice Options");
          }, "Billing");
        }
      }
    });
