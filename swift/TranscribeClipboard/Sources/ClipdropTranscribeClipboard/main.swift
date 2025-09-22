import AppKit
import Foundation
import UniformTypeIdentifiers

/// Returns the first audio file URL found on the general pasteboard.
/// Prefers UTType-based checks and falls back to a light extension check.
func firstAudioFileURLFromPasteboard() -> URL? {
  let pasteboard = NSPasteboard.general
  guard let items = pasteboard.pasteboardItems, !items.isEmpty else { return nil }

  for item in items {
    if let value = item.string(forType: .fileURL), let url = URL(string: value) {
      if let contentType = try? url.resourceValues(forKeys: [.contentTypeKey]).contentType,
         contentType.conforms(to: .audio) {
        return url
      }
      if [".m4a", ".mp3", ".wav", ".aiff", ".caf"].contains(url.pathExtension.lowercased().withDot) {
        return url
      }
    }
  }

  return nil
}

private extension String {
  var withDot: String { hasPrefix(".") ? self : "." + self }
}

@main
struct ClipdropTranscribeClipboardApp {
  static func main() {
    if let url = firstAudioFileURLFromPasteboard() {
      print("Found audio file URL: \(url.path)")
    } else {
      fputs("No audio file URL found on the clipboard.\n", stderr)
    }
  }
}
