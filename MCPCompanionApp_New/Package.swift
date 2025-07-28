// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MCPCompanion",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "MCPCompanion",
            targets: ["MCPCompanion"]
        )
    ],
    dependencies: [
        // Add any dependencies here if needed
    ],
    targets: [
        .executableTarget(
            name: "MCPCompanion",
            dependencies: [],
            path: "Sources"
        )
    ]
)
