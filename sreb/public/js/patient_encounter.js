// sreb — toggle Draft Invoice tab only when Encounter Type = "Order"
function toggle_draft_invoice_tab(frm) {
  const show = (frm.doc.encounter_type || "") === "Order";
  const fieldname = "draft_invoice";

  try { if (frm.fields_dict[fieldname]) frm.toggle_display(fieldname, show); } catch {}

  try {
    const $link = frm.$wrapper.find(`.form-tabs .nav-link[data-fieldname="${fieldname}"]`);
    if ($link.length) {
      $link.closest("li").toggle(!!show);
      if (!show && $link.hasClass("active")) {
        const $first = frm.$wrapper.find('.form-tabs .nav-link:visible').first();
        if ($first.length) $first.trigger('click');
      }
    }
  } catch {}

  try { frm.set_df_property(fieldname, "hidden", show ? 0 : 1); } catch {}
}

frappe.ui.form.on("Patient Encounter", {
  onload: toggle_draft_invoice_tab,
  refresh: toggle_draft_invoice_tab,
  encounter_type: toggle_draft_invoice_tab,
});
