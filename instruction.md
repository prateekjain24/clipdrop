# Aligning Swift Toolchain for ClipDrop Swift Helper Builds

Use these steps to configure another macOS machine so that `swift build` succeeds for the helper package in `swift/TranscribeClipboard`.

1. Verify Xcode installation
   - Run `ls /Applications | grep Xcode` to see available Xcode apps (e.g. `Xcode.app`, `Xcode-beta.app`).
   - If none are present, install the desired Xcode version from the Mac App Store or developer.apple.com and open it once to finish setup.

2. Point the command-line tools at the matching Xcode
   - Switch with `sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer` (adjust the path if you installed a beta, e.g. `Xcode-beta.app`).
   - Confirm with `xcode-select --print-path`; it should echo the same `/Applications/.../Contents/Developer` path.
   - Optionally check `xcodebuild -version` to ensure the selected toolchain matches the SDK you expect.

3. (Optional) Refresh Command Line Tools
   - If you only plan to use Command Line Tools, reinstall them so the compiler and SDK come from the same release:
     ```sh
     sudo rm -rf /Library/Developer/CommandLineTools
     xcode-select --install
     ```
   - After installation, either keep using the CLTs (`sudo xcode-select --switch /Library/Developer/CommandLineTools`) or switch back to full Xcode per step 2.

4. Build the helper
   - From the repository root: `cd swift/TranscribeClipboard`
   - Run `swift build`
   - You should see `Build complete!` and the binary at `.build/debug/clipdrop-transcribe-clipboard`.

If `swift build` still fails, re-run steps 1–3 to ensure the selected toolchain and SDK originate from the same Xcode release, and verify you’re building on macOS 15.4 or newer as required by the helper.
