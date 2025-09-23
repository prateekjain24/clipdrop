// swift-tools-version: 5.10
import PackageDescription

let package = Package(
  name: "ClipdropTranscribeClipboard",
  platforms: [.macOS("26.0")],
  products: [
    .executable(name: "clipdrop-transcribe-clipboard", targets: ["ClipdropTranscribeClipboard"])
  ],
  targets: [
    .executableTarget(
      name: "ClipdropTranscribeClipboard",
      path: "Sources/ClipdropTranscribeClipboard")
  ]
)
