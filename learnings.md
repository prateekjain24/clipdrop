# Learnings

## Apple SpeechAnalyzer API Implementation (macOS 26)

### Key Learnings from Swift TranscribeClipboard Development

#### 1. Swift Entry Point Conflicts
**Problem**: "'main' attribute cannot be used in a module that contains top-level code"

**Root Cause**: Having both a file named `main.swift` AND using `@main` attribute creates a conflict. Swift requires either:
- A file named `main.swift` (automatically becomes entry point)
- OR `@main` attribute on a struct/class
- Never both

**Solution**: Rename `main.swift` to any other name (e.g., `TranscribeClipboard.swift`) when using `@main`

#### 2. SpeechAnalyzer API Usage Patterns

**Incorrect Pattern** (causes "Cannot simultaneously analyze multiple input sequences"):
```swift
// DON'T DO THIS
let analyzer = SpeechAnalyzer(inputAudioFile: audioFile, modules: [transcriber])
let result = try await analyzer.analyzeSequence(from: audioFile) // Duplicate!
```

**Correct Pattern**:
```swift
// DO THIS
let analyzer = SpeechAnalyzer(modules: [transcriber])
let lastSampleTime = try await analyzer.analyzeSequence(from: audioFile)
```

#### 3. Async Result Consumption

**Problem**: Process hangs after transcription completes

**Root Cause**: Results must be consumed concurrently with analysis, not sequentially after

**Incorrect Pattern**:
```swift
// This will hang
let lastSampleTime = try await analyzer.analyzeSequence(from: audioFile)
for try await result in transcriber.results { // Waits forever
    // process results
}
```

**Correct Pattern**:
```swift
// Start consuming results concurrently
let resultsTask = Task {
    for try await result in transcriber.results {
        // process results
    }
}

// Then analyze
let lastSampleTime = try await analyzer.analyzeSequence(from: audioFile)

// Then finalize (this terminates the results stream)
try await analyzer.finalizeAndFinish(through: lastSampleTime)

// Wait for results to complete
try await resultsTask.value
```

#### 4. Locale Allocation and Fallbacks

**Problem**: "Cannot use modules with unallocated locales [en_SG]"

**Key Insights**:
- SpeechTranscriber requires locale assets to be installed
- Not all locales are supported (e.g., en_SG might not be)
- Implement intelligent fallbacks (en_SG → en_US)

**Solution Pattern**:
```swift
func getSupportedLocale(for requestedLocale: Locale) async -> Locale? {
    let supportedLocales = await SpeechTranscriber.supportedLocales

    // Try exact match first
    if let exact = supportedLocales.first(where: {
        $0.identifier(.bcp47) == requestedLocale.identifier(.bcp47)
    }) {
        return exact
    }

    // Implement fallback logic
    // e.g., en_SG -> en_US, zh_SG -> zh_CN
}
```

#### 5. Model Installation

Always check and install required models before transcription:
```swift
if let installRequest = try await AssetInventory.assetInstallationRequest(
    supporting: [transcriber]
) {
    try await installRequest.downloadAndInstall()
}
```

#### 6. Actor Isolation

Remember that SpeechAnalyzer is an actor. Methods like `cancelAndFinishNow()` require `await`:
```swift
await analyzer.cancelAndFinishNow() // Not just analyzer.cancelAndFinishNow()
```

### Platform Requirements

- macOS 26.0+ required for on-device transcription
- Update Package.swift: `platforms: [.macOS("26.0")]`
- Use availability checks: `@available(macOS 26.0, *)`

### Common Pitfalls to Avoid

1. **Don't** use both file-based and stream-based initialization simultaneously
2. **Don't** try to consume results after calling `analyzeSequence` - do it concurrently
3. **Don't** assume all locales are supported - always validate and provide fallbacks
4. **Don't** forget to call `finalizeAndFinish` to properly terminate streams
5. **Don't** forget the `await` keyword for actor-isolated methods

### Best Practices

1. Always provide clear error messages with locale information
2. Log important milestones (analysis start, finish, finalization)
3. Handle the case where no speech is detected
4. Use proper error handling with do-catch blocks
5. Clean up resources by properly finalizing the analyzer

### Testing Considerations

When testing transcription:
- Use stderr for logging: `fputs("[helper] message\n", stderr)`
- Redirect stderr to a log file: `command 2> helper.log`
- Ensure the process exits cleanly after transcription
- Test with various audio formats and locales