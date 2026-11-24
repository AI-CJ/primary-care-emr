"""Exercise clinical writes and permissions in the packaged WebAssembly API."""
from datetime import date, timedelta
import json

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:4174/primary-care-emr/"
PASSWORD = "Welcome-EMR-2026"


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL)
        page.evaluate("""() => {
          const worker = new Worker(new URL('runtime-worker.mjs', location.href), {type: 'module'});
          let id = 0;
          window.workerRequest = (request) => new Promise((resolve, reject) => {
            const current = ++id;
            const timer = setTimeout(() => reject(Error('Worker request timed out')), 120000);
            const handler = (event) => {
              if (event.data.id !== current) return;
              clearTimeout(timer);
              worker.removeEventListener('message', handler);
              if (event.data.error) reject(Error(event.data.error));
              else resolve(event.data.reply);
            };
            worker.addEventListener('message', handler);
            worker.postMessage({id: current, request});
          });
        }""")

        def request(method, path, data=None, token=None, expected=None):
            headers = [["content-type", "application/json"]]
            if token:
                headers.append(["authorization", f"Bearer {token}"])
            reply = page.evaluate("request => window.workerRequest(request)", {
                "url": "http://emr.local" + path, "method": method,
                "headers": headers, "body": json.dumps(data) if data is not None else "",
            })
            status = reply["status"]
            assert status == expected if expected is not None else 200 <= status < 300, (
                method, path, status, reply["body"]
            )
            return json.loads(reply["body"]) if reply["body"] else None

        def login(username):
            return request("POST", "/auth/login", {"username": username, "password": PASSWORD})["access_token"]

        admin = login("admin")
        patient = login("jordan.lee")
        request("GET", "/patients/2", token=patient, expected=403)
        appointments = request("GET", "/patients/1/appointments", token=admin)
        appointment = next(item for item in appointments if item["reason_for_visit"] == "Blood pressure follow-up")
        day = appointment["scheduled_date"]
        request("POST", f"/appointments/{appointment['id']}/check-in", token=admin)
        problem = request("POST", "/patients/1/problems", {"name": "Seasonal allergies"}, admin)
        medication = request("POST", "/patients/1/medications", {"name": "Example medication", "strength": "10 mg"}, admin)
        allergy = request("POST", "/patients/1/allergies", {"allergen": "Example allergen", "severity": "mild"}, admin)
        vital = request("POST", "/patients/1/vitals", {"recorded_on": day, "heart_rate": 72}, admin)
        note = request("POST", "/patients/1/encounters", {
            "visit_date": day, "appointment_id": appointment["id"],
            "reason_for_visit": "Blood pressure follow-up",
            "assessment": "Chart reviewed.", "plan": "Follow-up planned.",
            "patient_instructions": "Bring your readings to the next appointment.",
        }, admin)
        visit = f"/encounters/{note['id']}"
        for path, field, record in (
            ("problems", "problem_id", problem), ("medications", "medication_id", medication),
            ("allergies", "allergy_id", allergy), ("vitals", "vital_id", vital),
        ):
            request("POST", f"{visit}/{path}", {field: record["id"]}, admin)
            assert request("GET", f"{visit}/{path}", token=admin)
        order = request("POST", visit + "/lab-orders", {"test_name": "Follow-up panel"}, admin)
        referral = request("POST", visit + "/referrals", {"specialty": "Cardiology", "reason": "Follow-up"}, admin)
        request("POST", visit + "/finalize", token=admin)
        request("PUT", visit, {"visit_date": day, "reason_for_visit": "Altered", "assessment": "Attempted change."}, admin, expected=409)
        request("POST", visit + "/addenda", {"content": "Reviewed after finalization."}, admin)
        request("POST", f"/appointments/{appointment['id']}/complete", token=admin)
        request("POST", f"/lab-orders/{order['id']}/result", {
            "collected_on": day, "result_text": "Result recorded for review."
        }, admin)
        orders = request("GET", "/portal/lab-orders", token=patient)
        assert next(row for row in orders if row["id"] == order["id"])["result"] is None
        request("POST", f"/lab-orders/{order['id']}/result/release", token=admin)
        orders = request("GET", "/portal/lab-orders", token=patient)
        assert next(row for row in orders if row["id"] == order["id"])["result"] is not None
        request("POST", f"/referrals/{referral['id']}/complete", {
            "seen_on": day, "follow_up_summary": "Follow-up recorded."
        }, admin)
        goal = request("POST", "/patients/1/care-goals", {"title": "Review readings"}, admin)
        request("POST", f"/care-goals/{goal['id']}/progress", {"note": "Readings reviewed."}, admin)
        task = request("POST", "/patients/1/follow-up-tasks", {
            "title": "Review chart", "care_goal_id": goal["id"], "due_date": day,
        }, admin)
        new_due = (date.fromisoformat(day) + timedelta(days=3)).isoformat()
        request("POST", f"/follow-up-tasks/{task['id']}/reschedule", {
            "due_date": new_due, "reason": "Schedule adjusted."
        }, admin)
        request("POST", f"/follow-up-tasks/{task['id']}/complete", {"completion_note": "Reviewed."}, admin)
        request("POST", f"/care-goals/{goal['id']}/complete", {"completion_note": "Reviewed."}, admin)
        future = next(item for item in appointments if item["reason_for_visit"] == "Follow-up visit")
        change = request("POST", "/portal/appointment-change-requests", {
            "appointment_id": future["id"], "kind": "reschedule"
        }, patient)
        request("POST", f"/appointment-change-requests/{change['id']}/review", token=admin)
        assert any(item["status"] == "reviewed" for item in request("GET", "/portal/appointment-change-requests", token=patient))
        assert any(item["id"] == note["id"] for item in request("GET", "/portal/visits", token=patient))
        assert any(item["id"] == problem["id"] for item in request("GET", "/portal/problems", token=patient))
        for path in ("/portal/medications", "/portal/allergies", "/portal/vitals",
                     "/portal/care-goals", "/portal/referrals", "/portal/appointments",
                     "/patients/1/timeline", "/worklists/pending-lab-orders",
                     "/worklists/unreleased-lab-results", "/worklists/pending-referrals",
                     "/worklists/active-care-goals", "/worklists/open-follow-up-tasks",
                     "/admin/audit-events/activity"):
            request("GET", path, token=patient if path.startswith("/portal/") else admin)
        browser.close()
    print("Packaged clinical API smoke passed: appointment, records, linked note, finalization, lab release, referral, goals, follow-ups and portal requests.")


if __name__ == "__main__":
    run()
