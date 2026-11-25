"""Verify the exact published application and its isolated account workflows.

This check only accepts the project's public Pages URL or the disposable CI server.
It never submits real credentials or sends clinical records to an external API.
"""
import argparse
import json
import re
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

from scripts.check_browser_emr import URL as LOCAL_URL, TIMEOUT

PUBLIC_URL = "https://ai-cj.github.io/primary-care-emr/"


def verify_revision(url, revision):
    deadline = monotonic() + 120
    while monotonic() < deadline:
        try:
            request = Request(url + "release.json?revision=" + revision,
                              headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=15) as response:
                if response.geturl().split("?")[0] != url + "release.json":
                    raise ValueError("Unexpected release metadata redirect")
                metadata = json.load(response)
            if metadata.get("commit") == revision:
                print(f"Release identity verified: {revision}")
                return
        except (URLError, ValueError, OSError):
            pass
        sleep(5)
    raise RuntimeError("The expected release metadata was not available within 120 seconds")


def verify_workspace(url, revision):
    verify_revision(url, revision)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(30_000)
        errors = []
        external = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def guard(route):
            if route.request.url.startswith(url):
                route.continue_()
            else:
                external.append(route.request.resource_type)
                route.abort()

        page.route("**/*", guard)
        page.goto(url + "?revision=" + revision, wait_until="domcontentloaded")
        expect(page.get_by_role("note", name="Legal notice")).to_contain_text(
            "All provided patient records are fictional."
        )
        expect(page.get_by_text("Workspace ready.", exact=True)).to_be_visible(timeout=TIMEOUT)
        page.get_by_role("button", name="Sign in as Clinician").click()
        expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_visible(timeout=TIMEOUT)
        expect(page.get_by_role("button", name="Audit activity", exact=True)).to_have_count(0)
        page.get_by_role("button", name=re.compile("Find a patient")).click()
        page.get_by_role("button", name=re.compile("Lee, Jordan")).click()
        expect(page.get_by_role("heading", name="Jordan Lee", exact=True)).to_be_visible()
        expect(page.get_by_role("region", name="Active conditions")).to_contain_text(
            "Essential hypertension"
        )
        page.get_by_role("button", name="Sign out", exact=True).click()
        page.get_by_role("button", name="Switch to patient sign-in").click()
        page.get_by_role("button", name="Sign in as Jordan Lee").click()
        expect(page.get_by_role("heading", name="Your patient portal", exact=True)).to_be_visible(
            timeout=TIMEOUT
        )
        nav = page.get_by_role("navigation", name="Patient portal sections")
        nav.get_by_role("button", name="Test results & referrals", exact=True).click()
        expect(page.get_by_text("Lipid panel", exact=True)).to_be_visible()
        nav.get_by_role("button", name="Settings", exact=True).click()
        channel = page.get_by_label("Preferred contact method")
        expect(channel).to_have_value("portal")
        channel.select_option("email")
        page.get_by_role("button", name="Save preferences", exact=True).click()
        expect(page.get_by_text("Your communication preferences were saved.")).to_be_visible()
        page.once("dialog", lambda dialog: dialog.accept())
        page.get_by_role("button", name="Demo reset").click()
        expect(page.get_by_role("heading", name="Staff sign in", exact=True)).to_be_visible(timeout=TIMEOUT)
        page.get_by_role("button", name="Switch to patient sign-in").click()
        page.get_by_role("button", name="Sign in as Jordan Lee").click()
        nav.get_by_role("button", name="Settings", exact=True).click(timeout=TIMEOUT)
        expect(page.get_by_label("Preferred contact method")).to_have_value("portal")
        assert not errors, f"Browser errors: {len(errors)}"
        assert not external, f"Unexpected external requests: {external}"
        browser.close()
    verify_revision(url, revision)
    print(f"Verified {url}: release identity, clinician and patient access, shared result, preferences and reset.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--local", action="store_true",
                        help="Use the disposable local CI build rather than Pages")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.revision):
        parser.error("Expected a full Git commit SHA")
    verify_workspace(LOCAL_URL if args.local else PUBLIC_URL, args.revision)


if __name__ == "__main__":
    main()
