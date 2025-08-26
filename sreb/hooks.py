app_name = "sreb"
app_title = "Sreb"
app_publisher = "You"
app_description = "Encounter Billing helpers for ERPNext Healthcare"
app_email = "webdevelopersriaas@gmail.com"
app_license = "MIT"
required_apps = ["erpnext", "healthcare"]

doctype_js = {
    "Patient Encounter": "public/js/patient_encounter.js"
}

# Run our patch to create Custom Fields and Print Format
patches = [
    "sreb.patches.v1.install_basics"
]
