// swift-tools-version: 5.10
import PackageDescription

let package = Package(
  name: "ClipdropTransform",
  platforms: [.macOS("26.0")],
  products: [
    .executable(name: "clipdrop-transform", targets: ["ClipdropTransform"])
  ],
  targets: [
    .executableTarget(
      name: "ClipdropTransform",
      path: "Sources/ClipdropTransform"
    )
  ]
)
