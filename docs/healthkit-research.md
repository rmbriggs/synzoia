# HealthKit → web backend: bridge options

**Audience**: Teammate A, who owns sleep ingestion. Read this before picking a path.

**The core constraint**: HealthKit is iOS-only. There is no way to read it from a browser. Apple gates HealthKit through their native iOS SDK on a physical iPhone with the user signed in. Any "HealthKit on the web" solution actually goes through one of the bridges below.

The DB schema is source-agnostic — `sleep_posts.source` is one of `('manual','shortcut','healthkit_xml','terra','other')` — so picking a bridge is your call without breaking anyone else's work. Whatever bridge produces a body that maps to the `/api/sleep` shape works.

## Option 1 — Apple Shortcuts → POST (recommended starting point)

A Shortcut is a no-code iOS automation. The user installs a Shortcut you publish, it grabs last night's sleep from HealthKit on their iPhone, and POSTs it to `/api/sleep`.

**How it works**:
1. You build a Shortcut in the Shortcuts app on an iPhone.
2. Steps: "Get Health Sample" (Sleep Analysis, Last 24 hours) → "Get Dictionary from Input" → "Get Contents of URL" with POST to `https://synzoia.example.com/api/healthkit/import` and a Bearer token.
3. You export the Shortcut as an `.shortcut` file and host the share URL.
4. Users tap "Add Shortcut" once. Then they tap it once a morning, or schedule it via Personal Automation.

**Pros**:
- No iOS dev account, no Xcode, no native app.
- Real live-ish sync (whenever the user runs it).
- Free.
- Shortcut Personal Automations can run on a schedule with no user interaction (e.g., daily at 9am).

**Cons**:
- Setup is per-user and requires the user to install the Shortcut.
- Auth is awkward — you'd give each user a long-lived bearer token they paste into the Shortcut's URL.
- Apple has been making Personal Automations less reliable; "run daily at X" sometimes silently stops working.
- Limited error reporting — if a Shortcut fails, the user sees a vague notification.

**Body shape your `/api/healthkit/import` would accept**:
```json
{
  "user_token": "long-lived-bearer-or-api-key",
  "group_id": "uuid-of-target-crew",
  "samples": [
    {
      "start": "2026-05-15T23:32:00Z",
      "end": "2026-05-16T07:18:00Z",
      "stage": "inBed"
    },
    ...
  ]
}
```

Shortcuts can produce JSON via the "Dictionary" + "Get Contents of URL" action with a JSON body. The mapping from HealthKit's `HKCategoryValueSleepAnalysis` values to your `stage` enum (`awake|rem|core|deep`) is straightforward.

**Authentication path**: easiest is "user signs in to synzoia on the web, copies a long-lived API token from their settings page, pastes it into the Shortcut." Not as polished as OAuth, but bulletproof.

**Sample Apple Shortcut → cURL equivalent** (what the Shortcut actually sends):
```bash
curl -X POST https://synzoia.example.com/api/healthkit/import \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "abc-...",
    "samples": [{"start":"2026-05-15T23:32:00Z","end":"2026-05-16T07:18:00Z","stage":"inBed"}]
  }'
```

**Recommendation**: this is the lowest-effort path that produces a real demo. Start here, see if it's good enough.

## Option 2 — Third-party broker (Terra / Vital / Rook)

Companies that aggregate HealthKit + Fitbit + Oura + Whoop + Garmin behind one API. You integrate with one broker; users connect their data source through the broker; the broker pushes data to you via webhooks.

**Comparison**:

| Broker | Free tier (as of early 2026) | Coverage | Notes |
|---|---|---|---|
| **Terra** | 100 users, all sources | HealthKit (via Terra iOS SDK), Fitbit, Oura, Whoop, Garmin, many more | Best free tier. HealthKit requires their hosted-by-Terra mini iOS app or your own with their SDK. |
| **Vital** | Limited, pricing for startups | Similar coverage | More polished docs; less free. |
| **Rook** | Free for low volume | Similar | Less mature than Terra/Vital. |

**How it works (Terra-style)**:
1. You sign up for Terra, get an API key.
2. User clicks "Connect HealthKit" in synzoia → redirects to Terra's flow → user installs Terra's app or scans a QR code → grants Terra HealthKit permissions on their iPhone.
3. Terra starts pulling sleep data from HealthKit on the user's phone, pushes it to your webhook (`POST /api/healthkit/import` or wherever).
4. You verify the webhook signature, normalize the data into `sleep_posts`.

**Pros**:
- Solves "HealthKit now, wearables later" in one shot — Fitbit/Oura users work too.
- No per-user Shortcut setup.
- Real OAuth-style flow that feels professional.
- Webhooks are reliable; the broker retries failed deliveries.

**Cons**:
- External dependency. If Terra has an outage, your sync breaks.
- Free tier limits. 100 users at Terra is generous for a class demo but anchors you.
- Some flows (HealthKit specifically) still require a native iOS component — Terra provides their own, but it's a UX touchpoint they own.
- Webhook signature verification + idempotency are real work.

**Body shape (Terra's webhook)**:
```json
{
  "user": {"user_id": "terra-uuid", "reference_id": "your-synzoia-user-id"},
  "type": "sleep",
  "data": [
    {
      "metadata": {"start_time": "...", "end_time": "..."},
      "sleep_durations_data": {...},
      "sleep_quality_score": 82
    }
  ]
}
```

**Recommendation**: if you want the "Connect HealthKit" button to feel like a real product, this is the move. Cost: a few days to integrate Terra well, plus webhook handling.

## Option 3 — Manual XML export upload

Apple Health lets users export their entire Health database as a zipped XML file (Health app → tap profile picture → Export All Data). The user uploads the zip to synzoia; you parse the XML and ingest sleep records.

**How it works**:
1. User taps "Export All Data" in Apple Health on their iPhone.
2. AirDrops or emails themselves the `export.zip`.
3. Uploads it via a form in synzoia at `/settings/import`.
4. Backend unzips, parses `export.xml`, filters `Record` elements with `type="HKCategoryTypeIdentifierSleepAnalysis"`, batches into `sleep_posts`.

**Pros**:
- Zero external dependencies.
- Zero per-user setup beyond the upload.
- Works for everyone with an iPhone.

**Cons**:
- Not live. User has to re-export to get new nights.
- Exports are huge (years of data — can be 100MB+ zipped). Parse + filter takes seconds to minutes.
- UX is gross — "export all your health data, then upload it" is a sentence no one wants to read.
- Backfill semantics: re-uploading should be idempotent. Your `unique (user_id, group_id, night_of)` constraint handles this for you (use ON CONFLICT DO UPDATE).

**Recommendation**: useful as a fallback, especially for initial backfill ("I want to import the last 3 months"). Probably not the headline experience.

**Parsing sketch** (Python, using `lxml`):
```python
from lxml import etree
import zipfile

with zipfile.ZipFile(uploaded_zip) as z:
    with z.open("apple_health_export/export.xml") as f:
        tree = etree.parse(f)
        for record in tree.iter("Record"):
            if record.get("type") == "HKCategoryTypeIdentifierSleepAnalysis":
                start = record.get("startDate")
                end = record.get("endDate")
                value = record.get("value")  # HKCategoryValueSleepAnalysisAsleepCore, etc.
                # ...batch into sleep_posts + sleep_stages
```

## Option 4 — Native iOS companion app

A Swift app you build with HealthKit framework permission. Reads sleep data on the phone, POSTs to your backend.

**How it works**:
1. You build an iOS app in Xcode using HealthKit + URLSession.
2. App requests Sleep Analysis permission, reads samples, POSTs daily.
3. You distribute via TestFlight (free; 100 testers; needs Apple Developer Program account: $99/year, or you might be on UATX's account).

**Pros**:
- Best UX for live sync. App opens, data syncs, done.
- You own the whole pipeline.

**Cons**:
- It's a second product. Xcode, Swift, TestFlight, Apple Developer Program, App Store review eventually if you go past TestFlight.
- The class deliverable is a web app. The iOS app would be supplementary, not the demo.
- Realistically: a week+ of work for someone who hasn't shipped an iOS app before.

**Recommendation**: skip unless you've already shipped iOS apps and have Xcode set up. Not worth it for a 3-week class project.

## My honest take

If I were picking for a 3-week project with the constraint "it must work at the demo":

1. **Ship Option 1 (Shortcuts) for week 1-2 minimum viable HealthKit path.** Low risk, real working demo.
2. **If time allows, upgrade to Option 2 (Terra) in week 3** for the polished feel.
3. **Option 3 (XML upload) as the "want all my history" button** alongside whichever live-sync path you ship.
4. **Skip Option 4** unless someone on the team is already an iOS dev.

The professor will open the app in a browser and try to use it. They will not install your iOS companion. They will probably appreciate a clever Shortcut. They will be impressed by a working Terra integration. They will tolerate a manual XML upload.

## What you give the rest of the team

Once you pick a path, the rest of us need:

1. **The body shape of `/api/healthkit/import`**. Document it in the spec (§5) so leaderboard + streak code can rely on the resulting `sleep_posts` rows being correctly shaped.
2. **A test fixture** with 3-5 sample payloads in your chosen format, so backend tests don't need a real iPhone.
3. **A "how to connect" page** in the UI (`/settings/import` or similar) that walks a user through whatever the bridge needs.

Ping the rest of the team when you have these. Until then, manual entry through `POST /api/sleep` with `source: "manual"` is the working fallback.

## Links worth opening

- Apple's HealthKit framework docs: https://developer.apple.com/documentation/healthkit
- Apple Shortcuts user guide: https://support.apple.com/guide/shortcuts/welcome/ios
- Terra docs: https://docs.tryterra.co/
- Vital docs: https://docs.tryvital.io/
- Rook docs: https://docs.tryrook.io/
- Apple Health export format reference: search "Apple Health export.xml schema" — there's no official docs, but there are decent community write-ups.
