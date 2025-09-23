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

func firstAudioFileURLFromPasteboard() -> URL? {
  let pasteboard = NSPasteboard.general
  guard let items = pasteboard.pasteboardItems, !items.isEmpty else { return nil }

  for item in items {
    if let data = item.data(forType: .fileURL),
       let url = URL(dataRepresentation: data, relativeTo: nil, isAbsolute: true),
       url.isAudioFile {
      return url
    }

    if let raw = item.string(forType: .fileURL)?.trimmingCharacters(in: .whitespacesAndNewlines) {
      if let url = URL(string: raw), url.isAudioFile { return url }

      if raw.hasPrefix("file://"),
         let decoded = URL(string: raw)?.path,
         URL(fileURLWithPath: decoded).isAudioFile {
        return URL(fileURLWithPath: decoded)
      }

      let pathURL = URL(fileURLWithPath: raw)
      if pathURL.isAudioFile { return pathURL }
    }
  }

  return nil
}

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
func getSupportedLocale(for requestedLocale: Locale) async -> Locale? {
  let supportedLocales = await SpeechTranscriber.supportedLocales

  // Try exact match first
  if let exact = supportedLocales.first(where: {
    $0.identifier(.bcp47) == requestedLocale.identifier(.bcp47)
  }) {
    return exact
  }

  // Try language-only match (e.g., "en" from "en_SG")
  let requestedLang = requestedLocale.language.languageCode?.identifier
  if let requestedLang = requestedLang {
    // Preferred fallbacks for common languages
    let fallbackMap = [
      "en": ["en_US", "en_GB", "en_AU"],
      "zh": ["zh_CN", "zh_TW", "zh_HK"],
      "es": ["es_ES", "es_US", "es_MX"],
      "fr": ["fr_FR", "fr_CA", "fr_BE"],
      "de": ["de_DE", "de_CH", "de_AT"]
    ]

    if let fallbacks = fallbackMap[requestedLang] {
      for fallbackId in fallbacks {
        if let fallback = supportedLocales.first(where: {
          $0.identifier == fallbackId
        }) {
          fputs("[helper] Using fallback locale: \(fallback.identifier) for requested: \(requestedLocale.identifier)\n", stderr)
          return fallback
        }
      }
    }

    // Generic language match
    if let langMatch = supportedLocales.first(where: {
      $0.language.languageCode?.identifier == requestedLang
    }) {
      fputs("[helper] Using language match: \(langMatch.identifier) for requested: \(requestedLocale.identifier)\n", stderr)
      return langMatch
    }
  }

  return nil
}

@available(macOS 26.0, *)
func transcribeFile(at url: URL, lang: String?) async throws {
  let requestedLocale = lang.map(Locale.init(identifier:)) ?? Locale.current
  fputs("[helper] Opened \(url.path)\n", stderr)
  fputs("[helper] Requested locale: \(requestedLocale.identifier)\n", stderr)

  // Get supported locale with fallback
  guard let locale = await getSupportedLocale(for: requestedLocale) else {
    fputs("Error: Locale \(requestedLocale.identifier) not supported and no fallback available\n", stderr)
    fputs("Supported locales: \(await SpeechTranscriber.supportedLocales.map(\.identifier))\n", stderr)
    exit(2)
  }

  fputs("[helper] Using locale: \(locale.identifier)\n", stderr)

  // Create transcriber with the supported locale
  let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)

  // Check if models need to be installed
  if let installRequest = try await AssetInventory.assetInstallationRequest(
    supporting: [transcriber]
  ) {
    fputs("[helper] Downloading required models...\n", stderr)
    try await installRequest.downloadAndInstall()
    fputs("[helper] Models downloaded\n", stderr)
  }

  let audioFile = try AVAudioFile(forReading: url)
  let analyzer = SpeechAnalyzer(modules: [transcriber])

  fputs("[helper] analyzeSequence starting\n", stderr)

  var emitted = 0

  // Start consuming results concurrently
  let resultsTask = Task {
    do {
      for try await result in transcriber.results {
        fputs("[helper] received segment range=\(result.range)\n", stderr)
        let start = CMTimeGetSeconds(result.range.start)
        let duration = CMTimeGetSeconds(result.range.duration)
        let end = start + duration
        let text = String(result.text.characters)
        let json = #"{"start":\#(start.isFinite ? start : 0),"end":\#(end.isFinite ? end : start),"text":\#(text.jsonEscaped)}"#
        print(json)
        emitted += 1
      }
      fputs("[helper] results stream ended\n", stderr)
    } catch {
      fputs("[helper] results sequence error: \(error)\n", stderr)
      throw error
    }
  }

  // Start analysis
  let lastSampleTime = try await analyzer.analyzeSequence(from: audioFile)
  fputs("[helper] analyzeSequence finished: \(String(describing: lastSampleTime))\n", stderr)

  // Finish analysis (this will terminate the results stream)
  if let lastSampleTime {
    try await analyzer.finalizeAndFinish(through: lastSampleTime)
    fputs("[helper] analysis finalized\n", stderr)
  } else {
    await analyzer.cancelAndFinishNow()
    fputs("[helper] analysis cancelled\n", stderr)
  }

  // Wait for results task to complete
  try await resultsTask.value
  fputs("[helper] results task completed\n", stderr)

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

private extension URL {
  var isAudioFile: Bool {
    if let contentType = try? resourceValues(forKeys: [.contentTypeKey]).contentType,
       contentType.conforms(to: .audio) {
      return true
    }

    return [".m4a", ".mp3", ".wav", ".aiff", ".caf"].contains(pathExtension.lowercased().withDot)
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
        fputs("Processing audio: \(audioURL.path)\n", stderr)
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
