// swift-tools-version: 5.10
import PackageDescription

let package = Package(
  name: "ClipdropSuggestName",
  platforms: [.macOS("26.0")],
  products: [
    .executable(name: "clipdrop-suggest-name", targets: ["ClipdropSuggestName"])
  ],
  targets: [
    .executableTarget(
      name: "ClipdropSuggestName",
      path: "Sources/ClipdropSuggestName"
    )
  ]
)
