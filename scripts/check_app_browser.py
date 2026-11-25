"""Exercise the real synthetic application in Chromium against a disposable database."""
import os
import re
import secrets

from playwright.sync_api import expect, sync_playwright
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.account_auth import create_user_account
from backend.database import engine
from backend.models import Patient

URL = "http://127.0.0.1:5173/"
PASSWORD = secrets.token_urlsafe(24)


def create_smoke_accounts():
    # Never create test accounts against a deployed or normal development database.
    if (
        os.environ.get("EMR_RUN_SYNTHETIC_SMOKE") != "1"
        or engine.url.database != "emr_browser_smoke"
        or engine.url.host not in {"localhost", "127.0.0.1"}
    ):
        raise RuntimeError("Use only the disposable local emr_browser_smoke database.")
    with Session(engine) as session:
        patient_id = session.scalar(
            select(Patient.id).where(Patient.first_name == "Jordan", Patient.last_name == "Lee")
        )
        if patient_id is None:
            raise RuntimeError("Run the synthetic seed first.")
        create_user_account(session, username="smoke.clinician", password=PASSWORD,
                            account_type="staff", staff_role="clinician")
        create_user_account(session, username="smoke.admin", password=PASSWORD,
                            account_type="staff", staff_role="admin")
        create_user_account(session, username="smoke.patient", password=PASSWORD,
                            account_type="patient", patient_id=patient_id)
        session.commit()


def assert_legal_notice(page):
    notice = page.get_by_role("note", name="Legal notice")
    expect(notice).to_have_count(1)
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("All provided patient records are fictional.")
    expect(notice).to_contain_text("Do not enter real patient information")
    expect(page.get_by_role("button", name="Demo reset")).to_have_count(0)
    body = page.locator("body").inner_text().replace(notice.inner_text(), "", 1)
    assert not re.search(r"\b(synthetic|mock|fake|fictional|demo|portfolio|simulat\w*)\b", body, re.I), body


def sign_in(page, username):
    page.get_by_label("Username", exact=True).fill(username)
    page.get_by_label("Password", exact=True).fill(PASSWORD)
    page.get_by_role("button", name="Sign in", exact=True).click()


def open_chart(page):
    expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_visible()
    page.get_by_role("button", name="Find a patient", exact=False).click()
    expect(page.get_by_role("heading", name="Patient Search", exact=True)).to_be_visible()
    page.get_by_role("searchbox", name="Search patients").fill("Jordan")
    page.get_by_role("button", name="Search", exact=True).click()
    page.get_by_role("button", name="Lee, Jordan", exact=False).click()
    expect(page.get_by_role("heading", name="Jordan Lee", exact=True)).to_be_visible()
    assert_legal_notice(page)


def sign_out(page, mode):
    page.get_by_role("button", name="Sign out", exact=True).click()
    expect(page.get_by_role("heading", name=f"{mode} sign in", exact=True)).to_be_visible()


def assert_no_overflow(page):
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Horizontal overflow"


def run():
    create_smoke_accounts()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        desktop = browser.new_page(viewport={"width": 1280, "height": 900},
                                   reduced_motion="reduce")
        errors = []
        desktop.on("pageerror", lambda error: errors.append(str(error)))
        desktop.goto(URL)
        assert_legal_notice(desktop)
        sign_in(desktop, "smoke.clinician")
        open_chart(desktop)
        expect(desktop.get_by_role("heading", name="Active chart", exact=True)).to_be_visible()
        expect(desktop.get_by_text("Only administrators can change chart lifecycle status.")).to_be_visible()
        expect(desktop.get_by_role("button", name="Archive chart", exact=True)).to_have_count(0)
        sign_out(desktop, "Staff")

        sign_in(desktop, "smoke.admin")
        open_chart(desktop)
        desktop.get_by_role("button", name="Archive chart", exact=True).click()
        desktop.get_by_role("button", name="Confirm archive", exact=True).click()
        expect(desktop.get_by_role("heading", name="Archived chart", exact=True)).to_be_visible()
        sign_out(desktop, "Staff")

        desktop.get_by_role("button", name="Switch to patient sign-in").click()
        sign_in(desktop, "smoke.patient")
        expect(desktop.get_by_role("alert")).to_be_visible()
        expect(desktop.get_by_role("heading", name="Patient sign in", exact=True)).to_be_visible()
        desktop.get_by_role("button", name="Switch to staff sign-in").click()
        sign_in(desktop, "smoke.admin")
        open_chart(desktop)
        expect(desktop.get_by_role("heading", name="Archived chart", exact=True)).to_be_visible()
        desktop.get_by_role("button", name="Reactivate chart", exact=True).click()
        desktop.get_by_role("button", name="Confirm reactivate", exact=True).click()
        expect(desktop.get_by_role("heading", name="Active chart", exact=True)).to_be_visible()
        sign_out(desktop, "Staff")
        assert not errors, errors
        desktop.close()

        mobile = browser.new_page(viewport={"width": 360, "height": 800},
                                  reduced_motion="reduce")
        mobile_errors = []
        mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
        mobile.goto(URL)
        assert_legal_notice(mobile)
        assert_no_overflow(mobile)
        # Use the keyboard to activate the labeled account-mode control.
        switch = mobile.get_by_role("button", name="Switch to patient sign-in")
        switch.focus()
        switch.press("Enter")
        sign_in(mobile, "smoke.patient")
        expect(mobile.get_by_role("heading", name="My health summary")).to_be_visible()
        assert_legal_notice(mobile)
        mobile.get_by_role("navigation", name="Patient portal sections").get_by_role("button", name="Preferences").click()
        channel = mobile.get_by_label("Preferred contact method")
        expect(channel).to_have_value("portal")
        channel.select_option("email")
        mobile.get_by_role("button", name="Save preferences", exact=True).click()
        expect(mobile.get_by_text("Your communication preferences were saved.")).to_be_visible()
        assert_no_overflow(mobile)
        assert_legal_notice(mobile)
        sign_out(mobile, "Patient")
        sign_in(mobile, "smoke.patient")
        mobile.get_by_role("navigation", name="Patient portal sections").get_by_role("button", name="Preferences").click()
        expect(mobile.get_by_label("Preferred contact method")).to_have_value("email")
        sign_out(mobile, "Patient")
        assert not mobile_errors, mobile_errors
        mobile.close()
        browser.close()
    print("API-backed Chromium smoke passed: staff roles, chart lifecycle, patient sign-in and mobile preference persistence.")


if __name__ == "__main__":
    run()
