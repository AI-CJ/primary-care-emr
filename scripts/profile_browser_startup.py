"""Measure cold and cached repeat visits over a controlled local HTTP profile.

No synthetic timing estimates: run the real built app and count HTTP body bytes
at the origin, including worker assets. This is not a GitHub Pages benchmark.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from time import monotonic, sleep

from playwright.sync_api import expect, sync_playwright

RATE_BYTES = 2_500_000  # shared 20 Mbit/s payload budget
DELAY_SECONDS = 0.04  # per request, not an RTT model
TIMEOUT = 120_000


class ProfileOrigin(ThreadingHTTPServer):
    def __init__(self, directory):
        super().__init__(("127.0.0.1", 0), partial(ProfileHandler, directory=directory))
        self.transfer_lock = Lock()
        self.body_bytes = 0
        self.fail_archive = False


class ProfileHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_response(self, code, message=None):
        self.response_status = code
        super().send_response(code, message)

    def end_headers(self):
        # Same revision throughout both visits; never cache errors or the shell.
        cache = self.response_status == 200 and (
            "/runtime/" in self.path or "/assets/" in self.path
        )
        self.send_header("Cache-Control", "public, max-age=300" if cache else "no-store")
        super().end_headers()

    def do_GET(self):
        sleep(DELAY_SECONDS)
        if self.server.fail_archive and self.path.endswith("/runtime/backend.zip"):
            self.send_error(503, "Simulated archive outage")
            return
        super().do_GET()

    def copyfile(self, source, outputfile):
        # A single budget shared by all parallel requests, including workers.
        try:
            while chunk := source.read(64 * 1024):
                with self.server.transfer_lock:
                    sleep(len(chunk) / RATE_BYTES)
                    outputfile.write(chunk)
                    self.server.body_bytes += len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


def sign_in(page):
    start = monotonic()
    page.get_by_role("button", name="Sign in as Clinician", exact=True).click()
    expect(page.get_by_role("heading", name="Dashboard", exact=True)).to_be_visible(timeout=TIMEOUT)
    return monotonic() - start


def run():
    dist = Path("frontend/dist").resolve()
    assert (dist / "runtime/backend.zip").is_file(), "Build the browser application first"
    with TemporaryDirectory() as directory:
        (Path(directory) / "primary-care-emr").symlink_to(dist, target_is_directory=True)
        origin = ProfileOrigin(directory)
        thread = Thread(target=origin.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{origin.server_port}/primary-care-emr/"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context()
                external = []
                context.on("request", lambda request: external.append(request.url)
                           if not request.url.startswith(url) else None)
                samples = []
                for name in ("cold", "cached-repeat"):
                    before = origin.body_bytes
                    page = context.new_page()
                    page.on("console", lambda message: print(message.text)
                            if message.text.startswith("EMR startup ") else None)
                    start = monotonic()
                    page.goto(url, wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Staff sign in")).to_be_visible()
                    shell = monotonic() - start
                    expect(page.get_by_text("Workspace ready.", exact=True)).to_be_visible(timeout=TIMEOUT)
                    ready = monotonic() - start
                    login = sign_in(page)
                    page.close()
                    payload = origin.body_bytes - before
                    samples.append(payload)
                    print(f"Startup profile {name}: shell={shell:.3f}s ready={ready:.3f}s "
                          f"prepared_login={login:.3f}s origin_body_bytes={payload}")
                assert samples[0] > 0 and samples[1] < samples[0], samples
                assert not external, "Unexpected external request during startup"
                context.close()

                # A new context with an unavailable backend archive must report
                # failure, not create a partial workspace. Restore and reset.
                origin.fail_archive = True
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded")
                expect(page.get_by_text("Workspace preparation did not complete.", exact=False)).to_be_visible(timeout=TIMEOUT)
                expect(page.get_by_role("button", name="Sign out", exact=True)).to_have_count(0)
                origin.fail_archive = False
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="Demo reset").click()
                expect(page.get_by_text("Workspace ready.", exact=True)).to_be_visible(timeout=TIMEOUT)
                page.get_by_label("Username").fill("clinician")
                page.get_by_label("Password").fill("incorrect-password")
                page.get_by_role("button", name="Sign in", exact=True).click()
                expect(page.get_by_role("alert")).to_be_visible(timeout=TIMEOUT)
                expect(page.get_by_role("button", name="Sign out", exact=True)).to_have_count(0)
                sign_in(page)
                browser.close()
                print("Startup profile passed: cached repeat, failed archive/reset, invalid credentials and valid sign-in.")
        finally:
            origin.shutdown()
            origin.server_close()
            thread.join()


if __name__ == "__main__":
    run()
