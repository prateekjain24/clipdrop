# Apple Intelligence Availability (macOS 26)

## Hardware & OS gates
- **Mac hardware**: Any Mac with Apple silicon (M1 or later) running macOS 26 “Tahoe.” Intel Macs can install macOS 26, but Apple Intelligence remains unavailable on those machines.
- **Region & language**: Set **System Settings ▸ General ▸ Language & Region** to a supported language. Launch began with U.S. English, expanding in 2025 to additional English locales and more languages; keep Siri and device language aligned or the Use Model action stays hidden.
- **Apple ID requirements**: User must be 18+, signed in with iCloud, and have two-factor authentication enabled before the preview toggle appears. Apple exposes a waitlist when a device qualifies but demand exceeds capacity.

## Enable Apple Intelligence on macOS 26
1. Update to the latest macOS 26 point release (` ▸ System Settings ▸ General ▸ Software Update`). Check the release notes to confirm Apple Intelligence is included.
2. Open **System Settings ▸ Apple Intelligence & Siri**.
3. Toggle **Apple Intelligence** on. If you see “Join Waitlist,” enroll and wait for Apple’s confirmation push.
4. Review **Private Cloud Compute** settings—leave disabled for on-device-only workflows or enable to permit cloud escalations with PCC safeguards.
5. Optional: enable **ChatGPT** integration if you plan to route Use Model prompts to OpenAI when on-device coverage falls short.

## Runtime checks for developers
- Add a Swift helper in the App Intent extension that verifies Apple silicon hardware and macOS major version ≥ 26 before exposing Apple Intelligence-powered shortcuts.
- In Python, gate `clipdrop summarize` behind an `is_ai_available()` that inspects `platform.uname().machine` (`arm64` indicates Apple silicon) and parses `sw_vers -productVersion` ≥ `26`. Return a structured flag so the CLI prints “Apple Intelligence unavailable—use --no-ai” for unsupported Macs.

## Resources
- [Apple Intelligence is available today on iPhone, iPad, and Mac – Apple Newsroom](https://www.apple.com/newsroom/2024/10/apple-intelligence-is-available-today-on-iphone-ipad-and-mac/)
- [Apple Intelligence gets even more powerful across Apple devices – Apple Newsroom](https://www.apple.com/newsroom/2025/06/apple-intelligence-gets-even-more-powerful-with-new-capabilities-across-apple-devices/)
- [Apple Intelligence comes to iPhone, iPad, and Mac starting next month – Apple Newsroom](https://www.apple.com/newsroom/2024/09/apple-intelligence-comes-to-iphone-ipad-and-mac-starting-next-month/)
- [Introducing Apple Intelligence on Mac – Apple Support](https://support.apple.com/guide/mac-help/introducing-apple-intelligence-mchl46361784/mac)
- [Apple Intelligence is enabled by default in iOS 18.3 – The Verge](https://www.theverge.com/2025/1/21/24348850/apple-intelligence-ai-default-setting-ios-18-3)
