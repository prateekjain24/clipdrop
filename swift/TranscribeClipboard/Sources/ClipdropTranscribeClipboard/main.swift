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

/// Writes raw audio data from the pasteboard to a temporary file when no file URL exists.
func tempAudioFromPasteboard() -> URL? {
  let pasteboard = NSPasteboard.general
  guard let items = pasteboard.pasteboardItems, !items.isEmpty else { return nil }

  for item in items {
    for type in item.types {
      guard let utType = UTType(type.rawValue), utType.conforms(to: .audio) else { continue }
      guard let data = item.data(forType: type) else { continue }

      let ext = utType.preferredFilenameExtension ?? "m4a"
      let destination = URL(fileURLWithPath: NSTemporaryDirectory())
        .appendingPathComponent("clipdrop-\(UUID().uuidString)")
        .appendingPathExtension(ext)

      do {
        try data.write(to: destination, options: [.atomic])
        return destination
      } catch {
        // If writing fails, try the next matching item/type.
        continue
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
      return
    }

    if let tempURL = tempAudioFromPasteboard() {
      print("Wrote clipboard audio to temporary file: \(tempURL.path)")
      return
    }

    fputs("No audio file URL or raw audio data found on the clipboard.\n", stderr)
  }
}
