# Private Cloud Compute (PCC) Fundamentals

## Why PCC matters for ClipDrop
Apple Intelligence escalates heavy Use Model requests to PCC when on-device models are insufficient. Understanding PCC helps you explain privacy trade-offs to users and decide when to allow the `--no-ai` fallback.

## How PCC protects data
- **Apple silicon in the cloud**: PCC runs on custom servers with the same secure boot chain as iPhone and Mac, so only Apple-signed images can process requests.
- **Ephemeral access**: Every request uses a per-session encryption key. After the response is returned, both the key and the transient data buffer are destroyed.
- **Independent verification**: Apple publishes signed PCC images for external researchers to inspect. Community tools can verify the hash that shipped to production.
- **Transparency**: Requests are logged locally on-device so users can review or clear their history; Apple has no visibility unless the user opts to share diagnostics.

## Developer guidance
- Log whether a response came from On-Device or PCC (Shortcuts exposes this metadata via the Use Model action). Surface it in CLI output for troubleshooting.
- Offer a CLI flag (`clipdrop summarize --privacy strict`) that forces on-device execution and emits a warning if PCC would be required.
- Document PCC behavior in README/Privacy Policy—especially that inputs are encrypted, processed transiently, and never used to train models.

## Resources
- [Private Cloud Compute – Apple Security Research Blog](https://security.apple.com/blog/private-cloud-compute)
- [Apple details how Private Cloud Compute protects your data – 9to5Mac](https://9to5mac.com/2024/06/11/private-cloud-compute-explained/)
- [Apple’s Private Cloud Compute whitepaper – iMore summary](https://www.imore.com/software/ios/apple-publishes-whitepaper-on-private-cloud-compute-explaining-how-its-keeping-your-data-safe)
