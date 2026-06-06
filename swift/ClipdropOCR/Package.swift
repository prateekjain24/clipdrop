// swift-tools-version: 5.10
import PackageDescription

let package = Package(
  name: "ClipdropOCR",
  platforms: [.macOS("13.0")],
  products: [
    .executable(name: "clipdrop-ocr", targets: ["ClipdropOCR"])
  ],
  targets: [
    .executableTarget(
      name: "ClipdropOCR",
      path: "Sources/ClipdropOCR"
    )
  ]
)
