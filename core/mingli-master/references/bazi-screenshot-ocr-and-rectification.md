# Bazi screenshot OCR and birth-time rectification notes

Use when the user sends a bazi app screenshot and asks to infer or correct the birth time.

## What to extract first

- Name/nickname only if needed for identifying the screenshot; do not repeat private identity details unless the user asks.
- Sex/gender as displayed by the app.
- Birth place and timezone.
- Civil birth date and the displayed time.
- Four pillars, especially whether the screenshot time is a placeholder such as `12:00`.
- Any visible shensha list, but treat it as auxiliary evidence, not a time-correction anchor.

## OCR fallback pattern on macOS

If image vision analysis fails or cannot read the screenshot, use local OCR instead of guessing. A robust pattern is a tiny Swift script using Apple Vision OCR:

```swift
import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cgImage = bitmap.cgImage else { exit(2) }
let request = VNRecognizeTextRequest { request, error in
    let observations = request.results as? [VNRecognizedTextObservation] ?? []
    for obs in observations.sorted(by: { a,b in
        abs(a.boundingBox.origin.y - b.boundingBox.origin.y) > 0.015 ? a.boundingBox.origin.y > b.boundingBox.origin.y : a.boundingBox.origin.x < b.boundingBox.origin.x
    }) {
        if let top = obs.topCandidates(3).first { print(top.string) }
    }
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
```

Run with `swift /tmp/ocr.swift /path/to/image`.

## Rectification boundaries

- Do not claim a precise clock minute from bazi. Bazi can usually narrow to a two-hour 时辰; minute-level correction needs birth certificate, hospital record, or family record.
- If the app shows `12:00`, treat it as possibly a placeholder. If the true birth time is still within 11:00-12:59, the hour pillar remains 午时 and the displayed chart may still be usable.
- First fix the deterministic fact layer: civil birth date/time anchor, birthplace, timezone, lunar date, solar-term month, four pillars, hidden stems, ten gods, seasonal_tiaohou_profile.
- Then enumerate the 12 hour-pillar candidates and eliminate by known life events.

## Event prompts for narrowing

Ask for 3-5 verified events, preferably with years/months:

- parents relationship or family upheaval
- moves, leaving hometown, immigration, school/city changes
- education/major/career turning points
- first major relationship and breakup/commitment years
- health events, injuries, surgery, sleep/constitution patterns
- money/job shocks in recent years

## User-facing style

Lead with the practical constraint: `只能先校时辰，不能编具体几点几分`. Then say whether the displayed time still maps to the same 时辰. Keep the formal gate labels compact when calculation-sensitive: `【问题分类】`, `【事实层】`, `【加载的古籍包】`, `【文本依据】`, `【综合判断】`, `【边界与版本说明】`.