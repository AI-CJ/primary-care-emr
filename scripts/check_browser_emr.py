"""Exercise the deployed build without a networked API or shared database."""
import re
from playwright.sync_api import expect, sync_playwright

URL = "http://127.0.0.1:4174/primary-care-emr/"
TIMEOUT = 120_000


def sign_in(page, account):
    page.get_by_role("button", name=f"Sign in as {account}", exact=True).click()
    expect(page.get_by_role("button", name="Sign out", exact=True)).to_be_visible(timeout=TIMEOUT)


def search(page, name):
    if page.get_by_role("heading", name="Dashboard", exact=True).is_visible():
        staff_section(page, "Patients")
    page.get_by_role("searchbox", name="Search patients").fill(name)
    page.get_by_role("button", name="Search", exact=True).click()


def chart_section(page, name):
    nav = page.get_by_role("navigation", name="Patient chart sections")
    button = nav.get_by_role("button", name=name, exact=True)
    button.click()
    expect(button).to_have_attribute("aria-current", "page")


def portal_section(page, name):
    nav = page.get_by_role("navigation", name="Patient portal sections")
    button = nav.get_by_role("button", name=name, exact=True)
    button.click()
    expect(button).to_have_attribute("aria-current", "page")


def staff_section(page, name):
    nav = page.get_by_role("navigation", name="Staff workspace")
    button = nav.get_by_role("button", name=name, exact=True)
    button.click()
    expect(button).to_have_attribute("aria-current", "page")


def patient_mode(page):
    page.get_by_role("button", name="Switch to patient sign-in").click()


def sign_out(page):
    page.get_by_role("button", name="Sign out", exact=True).click()


def assert_notice(page):
    notice = page.get_by_role("note", name="Legal notice")
    expect(notice).to_have_count(1)
    expect(notice.get_by_role("button", name="Demo reset")).to_be_visible()
    expect(notice).to_contain_text("Not approved for clinical use")


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(30_000)
        # All runtime assets are served from the same origin. Block unexpected
        # HTTP traffic, including any attempt to send clinical records elsewhere.
        page.route("**/*", lambda route: route.continue_()
                   if route.request.url.startswith("http://127.0.0.1:4174/")
                   else route.abort())
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: print(message.text) if message.type == "error" else None)
        page.goto(URL)
        assert_notice(page)
        sign_in(page, "Administrator")
        expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Today's schedule", exact=True)).to_be_visible()
        expect(page.locator(".dashboard-metrics dd").first).to_have_text(re.compile(r"^[0-9]+$"), timeout=TIMEOUT)
        page.get_by_role("button", name="Find a patient", exact=False).click()
        # The directory is populated without an initial search.
        expect(page.get_by_role("button", name="Lee, Jordan", exact=False)).to_be_visible(timeout=TIMEOUT)
        staff_section(page, "Clinic Schedule")
        expect(page.get_by_role("heading", name="Clinic Schedule", exact=True)).to_be_visible()
        page.get_by_role("button", name="Jordan Lee", exact=True).click()
        expect(page.get_by_role("navigation", name="Patient chart sections").get_by_role("button", name="Appointments", exact=True)).to_have_attribute("aria-current", "page")
        page.get_by_role("button", name="Back to clinic schedule", exact=False).click()
        staff_section(page, "Patients")
        search(page, "Jordan")
        page.get_by_role("button", name="Lee, Jordan", exact=False).click()
        expect(page.get_by_role("heading", name="Jordan Lee", exact=True)).to_be_visible()
        chart_section(page, "Health record")
        expect(page.get_by_text("Essential hypertension", exact=True).first).to_be_visible()
        expect(page.get_by_text("Lisinopril 20 mg", exact=True).first).to_be_visible()
        page.get_by_role("button", name="+ Add Problem", exact=True).click()
        page.get_by_label("Problem *").fill("Seasonal allergies")
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.get_by_role("navigation", name="Patient chart sections").get_by_role("button", name="Summary", exact=True).click()
        expect(page.get_by_label("Problem *")).to_have_value("Seasonal allergies")
        page.get_by_role("button", name="Add Problem", exact=True).click()
        expect(page.get_by_text("Seasonal allergies", exact=True).first).to_be_visible()
        page.get_by_role("button", name="Edit Patient").click()
        page.get_by_label("Preferred name").fill("Jo")
        page.get_by_role("button", name="Save Changes", exact=True).click()
        expect(page.get_by_role("heading", name="Jordan (Jo) Lee")).to_be_visible()
        page.get_by_role("button", name="Back to patient search", exact=False).click()
        search(page, "Devin")
        page.get_by_role("button", name="Brooks, Devin", exact=False).click()
        page.get_by_role("button", name="Archive chart", exact=True).click()
        page.get_by_role("button", name="Confirm archive", exact=True).click()
        expect(page.get_by_role("heading", name="Archived chart")).to_be_visible()
        page.get_by_role("button", name="Reactivate chart", exact=True).click()
        page.get_by_role("button", name="Confirm reactivate", exact=True).click()
        expect(page.get_by_role("heading", name="Active chart")).to_be_visible()
        page.get_by_role("button", name="Back to patient search", exact=False).click()
        page.get_by_role("button", name="+ Add Patient", exact=True).click()
        page.get_by_label("First name *").fill("Avery")
        page.get_by_label("Last name *").fill("Reed")
        page.get_by_label("Date of birth *").fill("1990-01-01")
        page.get_by_label("Sex assigned at birth *").select_option("unknown")
        page.get_by_role("button", name="Save Patient", exact=True).click()
        expect(page.get_by_role("heading", name="Avery Reed")).to_be_visible()
        allergy_status = page.get_by_role("region", name="Chart allergy status")
        expect(allergy_status).to_contain_text("No allergies recorded; allergy status is not established.")
        allergy_status.get_by_role("button", name="Review health record").click()
        page.get_by_role("button", name="+ Add Allergy", exact=True).click()
        page.get_by_label("Allergen *").fill("Latex")
        page.get_by_label("Reaction").fill("Hives")
        page.get_by_label("Severity *").select_option("moderate")
        page.get_by_role("button", name="Add Allergy", exact=True).click()
        expect(allergy_status).to_contain_text("Latex")
        expect(allergy_status).to_contain_text("moderate severity; Hives")
        chart_section(page, "Visit notes")
        expect(allergy_status).to_contain_text("Latex")
        chart_section(page, "Health record")
        page.locator(".allergy-card").get_by_role("button", name="Edit", exact=True).click()
        page.locator(".allergy-card").get_by_label("Status *").select_option("inactive")
        page.locator(".allergy-card").get_by_role("button", name="Save Changes", exact=True).click()
        expect(allergy_status).to_contain_text("No active allergies recorded; historical records exist.")
        sign_out(page)
        patient_mode(page)
        sign_in(page, "Jordan Lee")
        expect(page.get_by_role("heading", name="Your patient portal", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Your next appointment", exact=True)).to_be_visible()
        page.get_by_role("button", name="My health Medications", exact=False).click()
        expect(page.get_by_role("heading", name="My health summary")).to_be_visible()
        expect(page.get_by_text("Essential hypertension", exact=True).first).to_be_visible()
        expect(page.get_by_text("Seasonal allergies", exact=True).first).to_be_visible()
        portal_section(page, "Preferences")
        channel = page.get_by_label("Preferred contact method")
        expect(channel).to_have_value("portal")
        channel.select_option("email")
        page.get_by_role("button", name="Save preferences", exact=True).click()
        expect(page.get_by_text("Your communication preferences were saved.")).to_be_visible()
        portal_section(page, "Appointments & visits")
        appointment = page.get_by_label("Scheduled visit")
        expect(appointment.locator("option")).not_to_have_count(1)
        appointment.select_option(index=1)
        page.get_by_label("Requested change").select_option("reschedule")
        page.get_by_role("button", name="Send request", exact=True).click()
        expect(page.get_by_text("Awaiting staff review", exact=True)).to_be_visible()
        sign_out(page)
        sign_in(page, "Jordan Lee")
        portal_section(page, "Preferences")
        expect(page.get_by_label("Preferred contact method")).to_have_value("email")
        assert_notice(page)
        sign_out(page)
        page.get_by_role("button", name="Switch to staff sign-in").click()
        sign_in(page, "Administrator")
        search(page, "Avery")
        expect(page.get_by_role("button", name="Reed, Avery", exact=False)).to_be_visible()
        page.get_by_role("button", name="Audit activity", exact=True).click()
        expect(page.get_by_role("heading", name="Audit activity")).to_be_visible()
        page.get_by_label("Event type").select_option("clinical_write")
        expect(page.get_by_role("cell", name="POST /patients", exact=True)).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role("button", name="Export CSV").click()
        assert download.value.suggested_filename == "audit-events.csv"
        staff_section(page, "Patients")
        search(page, "Avery")
        expect(page.get_by_role("button", name="Reed, Avery", exact=False)).to_be_visible()

        # Another browser context starts from the original records.
        other = browser.new_page(viewport={"width": 360, "height": 800})
        other.set_default_timeout(30_000)
        other.goto(URL)
        assert_notice(other)
        sign_in(other, "Clinician")
        expect(other.get_by_role("button", name="Audit activity", exact=True)).to_have_count(0)
        mobile_nav = other.get_by_role("combobox", name="Staff workspace", exact=True)
        expect(mobile_nav).to_be_visible()
        mobile_nav.select_option("schedule")
        expect(other.get_by_role("heading", name="Clinic Schedule", exact=True)).to_be_visible()
        mobile_nav.select_option("patients")
        search(other, "Avery")
        expect(other.get_by_text("No patients found.")).to_be_visible()
        assert other.evaluate("document.documentElement.scrollWidth <= innerWidth")
        other.close()

        # Cancelling reset must leave edits intact; accepting restores all data.
        page.once("dialog", lambda dialog: dialog.dismiss())
        page.get_by_role("button", name="Demo reset").click()
        expect(page.get_by_role("button", name="Reed, Avery", exact=False)).to_be_visible()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Demo reset").click()
        expect(page.get_by_role("heading", name="Staff sign in")).to_be_visible(timeout=TIMEOUT)
        sign_in(page, "Administrator")
        search(page, "Avery")
        expect(page.get_by_text("No patients found.")).to_be_visible()
        search(page, "Jordan")
        page.get_by_role("button", name="Lee, Jordan", exact=False).click()
        expect(page.get_by_role("heading", name="Jordan Lee", exact=True)).to_be_visible()
        sign_out(page)
        patient_mode(page)
        sign_in(page, "Jordan Lee")
        portal_section(page, "Health summary")
        expect(page.get_by_text("Essential hypertension", exact=True).first).to_be_visible()
        expect(page.get_by_text("Seasonal allergies", exact=True)).to_have_count(0)
        portal_section(page, "Preferences")
        expect(page.get_by_label("Preferred contact method")).to_have_value("portal")
        portal_section(page, "Appointments & visits")
        expect(page.get_by_text("No requests submitted yet.")).to_be_visible()
        assert not errors, errors
        browser.close()
    print("Interactive browser EMR smoke passed: edits, account roles, requests, tab isolation and reset.")


if __name__ == "__main__":
    run()
