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
func transcribeFile(at url: URL, lang: String?) async throws {
  let locale = lang.map(Locale.init(identifier:)) ?? Locale.current
  fputs("[helper] Opened \(url.path)\n", stderr)

  let transcriber = SpeechTranscriber(locale: locale, preset: .transcription)
  let audioFile = try AVAudioFile(forReading: url)
  let analyzer = try await SpeechAnalyzer(
    inputAudioFile: audioFile,
    modules: [transcriber],
    finishAfterFile: true
  )

  fputs("[helper] analyzeSequence starting\n", stderr)

  let analysisTask = Task {
    do {
      let result = try await analyzer.analyzeSequence(from: audioFile)
      fputs("[helper] analyzeSequence finished: \(String(describing: result))\n", stderr)
    } catch {
      fputs("[helper] analyzeSequence error: \(error)\n", stderr)
      throw error
    }
  }

  var emitted = 0
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
  } catch {
    fputs("[helper] results sequence error: \(error)\n", stderr)
    throw error
  }

  do {
    _ = try await analysisTask.value
    fputs("[helper] analysis task completed\n", stderr)
  } catch {
    fputs("[helper] analysis task failed: \(error)\n", stderr)
    throw error
  }

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
