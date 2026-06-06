import Foundation
import CoreGraphics
import ImageIO
import Vision

// clipdrop-ocr — extract text from an image using Apple's on-device Vision
// framework (VNRecognizeTextRequest). Reads an image file and prints the
// recognized text to stdout, one line per recognized block in approximate
// reading order.
//
// Usage:
//   clipdrop-ocr <image-path> [--lang en-US[,fr-FR,...]]
//
// Exit codes:
//   0  success (recognized text on stdout)
//   1  no text detected in the image
//   2  usage / load / recognition error (message on stderr)

func fail(_ message: String, code: Int32) -> Never {
    FileHandle.standardError.write(Data("clipdrop-ocr: \(message)\n".utf8))
    exit(code)
}

func loadCGImage(path: String) -> CGImage? {
    let url = URL(fileURLWithPath: path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        return nil
    }
    return image
}

// MARK: - Argument parsing

let arguments = Array(CommandLine.arguments.dropFirst())
guard let imagePath = arguments.first, !imagePath.hasPrefix("--") else {
    fail("usage: clipdrop-ocr <image-path> [--lang en-US]", code: 2)
}

var recognitionLanguages: [String] = []
var index = 1
while index < arguments.count {
    let arg = arguments[index]
    if arg == "--lang", index + 1 < arguments.count {
        recognitionLanguages = arguments[index + 1]
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        index += 2
    } else {
        index += 1
    }
}

guard let cgImage = loadCGImage(path: imagePath) else {
    fail("could not load image at \(imagePath)", code: 2)
}

// MARK: - Recognition

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
if !recognitionLanguages.isEmpty {
    request.recognitionLanguages = recognitionLanguages
}

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    fail("recognition failed: \(error.localizedDescription)", code: 2)
}

guard let observations = request.results, !observations.isEmpty else {
    exit(1)
}

// Vision uses a bottom-left origin with normalized coordinates, so a larger
// minY is higher on the page. Sort top-to-bottom, then left-to-right to
// approximate natural reading order.
let ordered = observations.sorted { lhs, rhs in
    if abs(lhs.boundingBox.minY - rhs.boundingBox.minY) > 0.01 {
        return lhs.boundingBox.minY > rhs.boundingBox.minY
    }
    return lhs.boundingBox.minX < rhs.boundingBox.minX
}

var lines: [String] = []
for observation in ordered {
    if let candidate = observation.topCandidates(1).first {
        let text = candidate.string.trimmingCharacters(in: .whitespacesAndNewlines)
        if !text.isEmpty {
            lines.append(text)
        }
    }
}

guard !lines.isEmpty else {
    exit(1)
}

print(lines.joined(separator: "\n"))
exit(0)
