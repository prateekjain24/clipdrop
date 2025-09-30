// swift-tools-version: 5.10
import PackageDescription

let package = Package(
  name: "ClipdropSummarize",
  platforms: [.macOS("26.0")],
  products: [
    .executable(name: "clipdrop-summarize", targets: ["ClipdropSummarize"])
  ],
  targets: [
    .executableTarget(
      name: "ClipdropSummarize",
      path: "Sources/ClipdropSummarize"
    )
  ]
)
