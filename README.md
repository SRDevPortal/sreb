# sreb (updated minimal app)
Auto-creates **DRAFT Sales Invoice** and **DRAFT Payment Entry(ies)** from
**Patient Encounter** when *Encounter Type = "Order"*.

- Hides the **Draft Invoice** tab unless Encounter Type = Order
- On save (after_save), if Order and items exist:
  - Create draft Sales Invoice from "Draft Invoice" tab
  - Create draft Payment Entries linked to the SI
  - Store the SI name on the Encounter (Generated Sales Invoice) to avoid duplicates
- No practitioner fields and no link filters

### Requirements
- Apps: `erpnext`, `healthcare`
- Child DocTypes included:
  - **Encounter Draft Item** (item, quantity, rate, amount)
  - **Encounter Draft Payment** (mode_of_payment, amount)
