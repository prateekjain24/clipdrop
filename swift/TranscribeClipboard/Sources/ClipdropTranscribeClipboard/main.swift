import AppKit
import AVFoundation
import CoreMedia
import Foundation
import Speech
import UniformTypeIdentifiers

struct Args {
  var lang: String? = nil
  var jsonl: Bool = true
}

func parseArgs() -> Args {
  var args = Args()
  var iterator = CommandLine.arguments.dropFirst().makeIterator()

  while let token = iterator.next() {
    switch token {
    case "--lang":
      if let value = iterator.next() {
        args.lang = value
      }
    case "--no-jsonl":
      args.jsonl = false
    default:
      break
    }
  }

  return args
}

func requirePlatformOrExit() {
  guard #available(macOS 26.0, *) else {
    fputs("On-device transcription requires macOS 26.0+.\n", stderr)
    exit(2)
  }
}

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
        continue
      }
    }
  }

  return nil
}

@available(macOS 26.0, *)
func transcribeFile(at url: URL, lang: String?) async throws {
  let locale = lang.map(Locale.init(identifier:)) ?? Locale.current
  let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)
  let audioFile = try AVAudioFile(forReading: url)

  let analyzer = try await SpeechAnalyzer(
    inputAudioFile: audioFile,
    modules: [transcriber],
    finishAfterFile: true
  )

  let analysisTask = Task {
    try await analyzer.start(inputAudioFile: audioFile, finishAfterFile: true)
  }

  var emitted = 0
  for try await result in transcriber.results {
    let start = CMTimeGetSeconds(result.range.start)
    let duration = CMTimeGetSeconds(result.range.duration)
    let end = start + duration
    let text = String(result.text.characters)
    let json = #"{"start":\#(start.isFinite ? start : 0),"end":\#(end.isFinite ? end : start),"text":\#(text.jsonEscaped)}"#
    print(json)
    emitted += 1
  }

  _ = try await analysisTask.value

  if emitted == 0 {
    fputs("No speech detected.\n", stderr)
    exit(3)
  }
}

private extension String {
  var withDot: String { hasPrefix(".") ? self : "." + self }
  var jsonEscaped: String {
    let escaped = self
      .replacingOccurrences(of: "\\", with: "\\\\")
      .replacingOccurrences(of: "\"", with: "\\\"")
      .replacingOccurrences(of: "\n", with: "\\n")
    return "\"\(escaped)\""
  }
}

@main
struct ClipdropTranscribeClipboardApp {
  static func main() async {
    requirePlatformOrExit()
    let args = parseArgs()

    let url = firstAudioFileURLFromPasteboard() ?? tempAudioFromPasteboard()
    guard let audioURL = url else {
      fputs("No audio file URL or raw audio data found on the clipboard.\n", stderr)
      exit(1)
    }

    if #available(macOS 26.0, *) {
      do {
        try await transcribeFile(at: audioURL, lang: args.lang)
      } catch {
        fputs("Transcription failed: \(error)\n", stderr)
        exit(4)
      }
    } else {
      exit(2)
    }
  }
}
