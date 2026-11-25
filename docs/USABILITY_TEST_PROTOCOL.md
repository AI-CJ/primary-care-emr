# Accessibility and usability verification protocol

## Purpose

Evaluate the actual Primary Care EMR application with fictional records. This is a small formative usability evaluation, not clinical research, a clinical safety certification, or a claim of WCAG conformance. Do not enter personal medical information, actual patient information, or real credentials. Use only the public isolated workspace or the disposable local build. Reset between sessions.

Automated accessibility checks inspect Chromium's accessibility tree, landmark count, heading order, control names, form labels, live status regions, hidden draft forms, keyboard navigation, sampled computed contrast, and reflow at 768, 360 and 320 CSS pixels. Run them against the browser build:

```bash
# Build and serve the isolated application using frontend/README.md.
python -m scripts.check_accessibility
```

The browser accessibility tree is an intermediate representation that screen readers use. Passing these checks does not establish the actual spoken output or a person's ability to complete the task.

## Manual screen-reader sessions

Use participants' normal assistive technology and record the exact application revision, operating system, browser, assistive technology version, viewport, zoom and input method. At minimum cover:

| Environment | Method |
| --- | --- |
| Windows 11 + Firefox or Chrome | NVDA, keyboard only |
| macOS + Safari | VoiceOver with keyboard |
| iOS + Safari | VoiceOver with touch |
| Android + Chrome | TalkBack with touch |

Begin on the sign-in page. Use headings, landmarks and the skip link to locate the content. Navigate in reading order without a pointer. Verify the account choices have meaningful names and descriptions; workspace readiness and sign-in errors are announced; the destination heading receives focus after mode changes, authentication and navigation. Check that the staff and patient navigation identifies the active section, patient chart identity and allergy status are understandable, action labels are distinct, and clinical status is not conveyed by color alone.

In patient settings, change the contact method, navigate away and confirm that the hidden form is not announced or keyboard-accessible. Return and verify the draft persists. Save and listen for the confirmation. Cancel sign-out with a modified draft and verify the form remains intact. Review released results and distinguish pending and unreleased records. Test native dialogs, keyboard focus after cancellation, sign-out and reset.

Repeat at 200% browser zoom; test reflow at a 320 CSS pixel viewport, text spacing overrides, forced colors/high contrast, reduced motion and mobile orientation. Inspect focused controls near sticky chart headers. Note any focus obstruction, unlabeled control, missing announcement, unexpected navigation, incorrect reading order, clipped text or touch target that cannot be activated. Automated viewport testing is not a substitute for these manual checks.

## Representative-user evaluation

Recruit approximately five staff participants familiar with outpatient workflows and five patients or patient-portal users, including people who use assistive technology or have limited digital confidence. This is a practical formative sample, not a statistically representative study. Obtain voluntary informed agreement. Do not recruit through actual clinical records, collect medical histories, or ask participants to disclose real diagnoses. Record only anonymous participant codes and task observations. If recording a session, obtain separate explicit consent.

The facilitator should provide the account role and scenario, but avoid showing the navigation path. Offer the same neutral prompt to each participant. Start each session with the original seeded data. Ask participants to think aloud if comfortable. Stop or provide help if a participant is distressed or cannot proceed.

| ID | Role | Scenario | Successful outcome |
| --- | --- | --- | --- |
| S1 | Clinician | Find Jordan Lee and identify current conditions, medication and recorded allergy status | Correct chart, correct source record, distinguishes unknown allergy status from confirmed absence |
| S2 | Clinician | Open today's schedule and enter the linked visit workflow | Correct chart and appointment, no accidental completion |
| S3 | Clinician | Save a draft note, find it again, and review finalization | Draft retained; participant recognizes finalization is a separate confirmed action |
| S4 | Clinician | Locate the result awaiting release and review it | Correct worklist, patient, and release status; does not share an unrelated result |
| S5 | Administrator | Locate audit activity and archive/reactivate the eligible fictional chart | Correct role, explicit confirmation, no unintended archive |
| P1 | Patient | Sign in as Jordan Lee and find the next appointment | Correct date/time and reason, distinguishes appointments from requests |
| P2 | Patient | Find a current medication and a released result | Correct patient record, no interpretation of unavailable results |
| P3 | Patient | Request a reschedule of an eligible appointment | Request appears in history; participant understands the appointment has not changed |
| P4 | Patient | Change a communication preference, navigate away, return and save | Draft retained, saved confirmation recognized, participant understands no message is sent |
| P5 | Patient | Identify sign-out and restore the starting workspace | Correct sign-out and explicit reset confirmation; understands reset removes edits |

Use a fresh session for workflows affected by earlier mutations. For each task record success independently, success with assistance, failure, time from scenario presentation, unnecessary actions, wrong chart selection, safety-critical error, and participant-reported difficulty (1 very difficult to 7 very easy). Record the actual words or behavior supporting a finding without identifying the person. Do not infer a success from a test script. Use the post-session prompt: "What was unclear, and what would you change?"

## Record sheet

```text
Revision:
Participant code:
Role:
Device/browser/assistive technology:
Task ID:
Outcome (independent / assisted / failed):
Elapsed seconds:
Navigation/actions:
Observed error or safety concern:
Difficulty (1–7):
Anonymous observation:
Proposed change:
Retest outcome:
```

Prioritize incorrect patient selection, unintended changes, hidden or mislabeled actions, inaccessible navigation, and loss of a draft above cosmetic findings. Resolve critical defects and retest the affected task. Compare measured task results against a baseline using the same task and device conditions. Report sample size and limitations; do not infer broad clinical usability, compliance, or improved time from automated test outcomes.

## Status

Manual screen-reader sessions and representative-user sessions require actual participants and hardware/software. They have not been conducted. The automated checks and their CI results are separate evidence. Store any subsequent anonymized findings in a dated report with the tested revision; do not publish identifying participant information.
