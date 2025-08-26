app_name = "sreb"
app_title = "Sreb"
app_publisher = "You"
app_description = "Auto draft invoice & payments from Patient Encounter"
app_email = "webdevelopersriaas@gmail.com"
app_license = "MIT"
required_apps = ["erpnext", "healthcare"]

# Only toggling the Draft Invoice tab (no buttons/filters)
doctype_js = {
    "Patient Encounter": "public/js/patient_encounter.js"
}

# Auto-create billing on save
doc_events = {
    "Patient Encounter": {
        "after_save": "sreb.events.patient_encounter.auto_make_draft_billing"
    }
}

# Create custom fields & tables wiring
patches = [
    "sreb.patches.v1.install_basics"
]
