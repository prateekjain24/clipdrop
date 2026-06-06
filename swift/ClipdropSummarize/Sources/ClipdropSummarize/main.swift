import Foundation
import FoundationModels

@main
struct ClipdropSummarizeApp {
    private static let structuredSummaryInstructions = """
You are an expert summarization assistant. Read the provided content and populate the summary fields:
- overall: a single sentence capturing the core message.
- keyTakeaways: the most important insights (at most three).
- actionItems: concrete next steps (at most three; leave empty if there are none).
- questions: open issues or uncertainties (at most three; leave empty if there are none).
Keep each entry concise (≤20 words), fact-based, and drawn directly from the source. Include names, dates, and metrics when present. Never ask the user to provide more text.
"""

    private static let chunkInstructions = """
You summarize long documents by first summarizing each section and then combining the results.
For each section you receive, produce concise bullet-ready takeaways in plain language. Capture unique facts, decisions, action items, and open questions. Avoid meta commentary or requests for more input. Output should be well-formed sentences suitable for markdown bullets.
"""

    private static let singlePassLimit = 15_000
    private static let placeholderMessage = "Model returned placeholder response"

    static func main() async {
        let result: SummaryResult

        do {
            let data = FileHandle.standardInput.readDataToEndOfFile()
            result = try await processInput(data: data)
        } catch let failure as SummarizationFailure {
            result = failure.toResult()
        } catch {
            result = SummaryResult(
                success: false,
                summary: nil,
                error: "Unexpected error: \(error)",
                retryable: false,
                stage: nil,
                warnings: nil,
                stageResults: nil,
                mode: nil,
                version: nil,
                elapsedMs: nil
            )
        }

        print(result.toJSON())
        exit(result.success ? 0 : 1)
    }

    private static func processInput(data: Data) async throws -> SummaryResult {
        let systemModel = SystemLanguageModel.default
        guard case .available = systemModel.availability else {
            let message = availabilityMessage(for: systemModel.availability)
            throw SummarizationFailure(message: message, stage: "precheck", retryable: false)
        }

        guard let inputText = String(data: data, encoding: .utf8) else {
            throw SummarizationFailure(message: "Invalid input encoding", stage: "precheck", retryable: false)
        }

        if let request = decodeChunkedRequest(from: data) {
            return try await handleChunked(request: request)
        }

        return try await handleSinglePass(text: inputText)
    }

    private static func handleSinglePass(text: String) async throws -> SummaryResult {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            throw SummarizationFailure(message: "Content is empty", stage: "precheck", retryable: false)
        }

        guard trimmed.count <= singlePassLimit else {
            throw SummarizationFailure(message: "Content too long for summarization", stage: "precheck", retryable: false)
        }

        // Guided generation guarantees the structure; on any model/availability
        // error this propagates out and the Python caller applies its local
        // fallback summary.
        let structured = try await runStructuredModel(
            prompt: Prompt("Summarize the following content.\n\n\(trimmed)"),
            instructions: structuredSummaryInstructions,
            options: GenerationOptions(
                sampling: nil,
                temperature: 0.3,
                maximumResponseTokens: 500
            ),
            stage: nil
        )

        return SummaryResult(
            success: true,
            summary: renderMarkdown(structured, note: nil),
            error: nil,
            retryable: nil,
            stage: nil,
            warnings: nil,
            stageResults: nil,
            mode: "single",
            version: nil,
            elapsedMs: nil
        )
    }

    private static func handleChunked(request: ChunkedSummarizationRequest) async throws -> SummaryResult {
        guard let chunks = request.chunks, !chunks.isEmpty else {
            throw SummarizationFailure(message: "No chunks provided", stage: "precheck", retryable: false)
        }

        let start = Date()
        var stageResults: [StageResult] = [StageResult(stage: "precheck", status: "ok", processed: nil, progress: 5)]
        var warnings: [String] = []

        let sortedChunks = chunks.sorted { lhs, rhs in
            switch (lhs.index, rhs.index) {
            case let (l?, r?):
                return l < r
            case (nil, _?):
                return true
            case (_?, nil):
                return false
            default:
                return (lhs.id ?? "") < (rhs.id ?? "")
            }
        }

        var chunkSummaries: [ChunkSummary] = []
        chunkSummaries.reserveCapacity(sortedChunks.count)

        let summaryOptions = GenerationOptions(
            sampling: nil,
            temperature: 0.3,
            maximumResponseTokens: 200
        )

        let chunkInstructionText = request.instructions?.isEmpty == false ? request.instructions! : chunkInstructions

        for (idx, chunk) in sortedChunks.enumerated() {
            let snippet = chunk.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            guard !snippet.isEmpty else {
                warnings.append("Chunk \(chunk.displayName) was empty and skipped")
                continue
            }

            if let limit = request.strategy?.maxChunkChars, let length = chunk.charLength, length > limit {
                warnings.append("Chunk \(chunk.displayName) exceeded max_chunk_chars (\(length) > \(limit))")
            }

            do {
                let prompt = Prompt("""
Summarize the following section in a short paragraph:

\(snippet)
""")
                let chunkSummary = try await runModel(
                    prompt: prompt,
                    instructions: chunkInstructionText,
                    options: summaryOptions,
                    stage: "chunk_summaries"
                )

                chunkSummaries.append(
                    ChunkSummary(id: chunk.id ?? "chunk-\(idx)", index: chunk.index ?? idx, summary: chunkSummary)
                )
            } catch let failure as SummarizationFailure {
                if failure.message == placeholderMessage || failure.message == "Content too long for processing" {
                    let fallback = fallbackChunkTakeaway(from: snippet)
                    if !fallback.isEmpty {
                        warnings.append("Chunk \(chunk.displayName) used fallback summarization")
                        chunkSummaries.append(
                            ChunkSummary(id: chunk.id ?? "chunk-\(idx)", index: chunk.index ?? idx, summary: fallback)
                        )
                        continue
                    }
                }

                let progress = Int(Double(idx) / Double(sortedChunks.count) * 70.0)
                stageResults.append(StageResult(stage: "chunk_summaries", status: "error", processed: idx, progress: progress))
                throw SummarizationFailure(
                    message: failure.message,
                    stage: failure.stage ?? "chunk_summaries",
                    retryable: failure.retryable,
                    stageResults: stageResults
                )
            }
        }

        if chunkSummaries.isEmpty {
            stageResults.append(StageResult(stage: "chunk_summaries", status: "error", processed: 0, progress: 0))
            throw SummarizationFailure(
                message: "No valid chunks to summarize",
                stage: "chunk_summaries",
                retryable: false,
                stageResults: stageResults
            )
        }

        stageResults.append(
            StageResult(
                stage: "chunk_summaries",
                status: "ok",
                processed: chunkSummaries.count,
                progress: 70
            )
        )

        let targetSentences = request.strategy?.targetSummarySentences ?? 4

        // Use hierarchical aggregation if we have too many chunks
        let summariesToAggregate: [ChunkSummary]
        if chunkSummaries.count > 8 {
            // Perform intermediate aggregation in batches
            let batchSize = 5
            var intermediateSummaries: [ChunkSummary] = []
            let batches = stride(from: 0, to: chunkSummaries.count, by: batchSize).map { startIndex -> ArraySlice<ChunkSummary> in
                let endIndex = min(startIndex + batchSize, chunkSummaries.count)
                return chunkSummaries[startIndex..<endIndex]
            }

            let intermediateInstructions = """
Combine the following section summaries into a single concise paragraph that captures all key information. Maintain factual accuracy and include important details.
"""

            for (batchIndex, batch) in batches.enumerated() {
                let batchPrompt = buildAggregationPrompt(from: Array(batch), targetSentences: targetSentences)

                do {
                    let intermediateSummary = try await runModel(
                        prompt: Prompt(batchPrompt),
                        instructions: intermediateInstructions,
                        options: GenerationOptions(
                            sampling: nil,
                            temperature: 0.3,
                            maximumResponseTokens: 200
                        ),
                        stage: "intermediate_aggregation"
                    )

                    intermediateSummaries.append(
                        ChunkSummary(
                            id: "batch-\(batchIndex)",
                            index: batchIndex,
                            summary: intermediateSummary
                        )
                    )
                } catch let failure as SummarizationFailure {
                    if failure.message == placeholderMessage {
                        // Use fallback for this batch
                        let fallbackBatchSummary = fallbackSummary(fromChunks: Array(batch), targetSentences: 2, note: nil)
                        intermediateSummaries.append(
                            ChunkSummary(
                                id: "batch-\(batchIndex)",
                                index: batchIndex,
                                summary: fallbackBatchSummary
                            )
                        )
                        warnings.append("Batch \(batchIndex + 1) used fallback summarization")
                        continue
                    }

                    stageResults.append(StageResult(stage: "intermediate_aggregation", status: "error", processed: batchIndex, progress: 75))
                    throw SummarizationFailure(
                        message: failure.message,
                        stage: failure.stage ?? "intermediate_aggregation",
                        retryable: failure.retryable,
                        stageResults: stageResults
                    )
                }
            }

            stageResults.append(
                StageResult(
                    stage: "intermediate_aggregation",
                    status: "ok",
                    processed: batches.count,
                    progress: 85
                )
            )

            summariesToAggregate = intermediateSummaries
        } else {
            summariesToAggregate = chunkSummaries
        }

        let aggregationPrompt = buildAggregationPrompt(from: summariesToAggregate, targetSentences: targetSentences)

        let aggregateInstructions: String
        if let custom = request.instructions, !custom.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            aggregateInstructions = custom
        } else {
            aggregateInstructions = structuredSummaryInstructions
        }

        let finalSummary: String
        do {
            let structured = try await runStructuredModel(
                prompt: Prompt(aggregationPrompt),
                instructions: aggregateInstructions,
                options: GenerationOptions(
                    sampling: nil,
                    temperature: 0.3,
                    maximumResponseTokens: 320
                ),
                stage: "aggregation"
            )
            finalSummary = renderMarkdown(structured, note: nil)
        } catch let failure as SummarizationFailure {
            if failure.message == placeholderMessage || failure.message == "Content too long for processing" {
                let fallback = fallbackSummary(fromChunks: chunkSummaries, targetSentences: targetSentences, note: "Fallback summary generated due to unavailable model output")
                let elapsedMs = Int(Date().timeIntervalSince(start) * 1000)
                warnings.append("Aggregation used fallback summarization")
                stageResults.append(StageResult(stage: "aggregation", status: "fallback", processed: nil, progress: 100))
                return SummaryResult(
                    success: true,
                    summary: fallback,
                    error: nil,
                    retryable: nil,
                    stage: nil,
                    warnings: warnings,
                    stageResults: stageResults,
                    mode: request.mode ?? "chunked",
                    version: request.version ?? "1.0",
                    elapsedMs: elapsedMs
                )
            }

            stageResults.append(StageResult(stage: "aggregation", status: "error", processed: nil, progress: 90))
            throw SummarizationFailure(
                message: failure.message,
                stage: failure.stage ?? "aggregation",
                retryable: failure.retryable,
                stageResults: stageResults
            )
        }

        stageResults.append(StageResult(stage: "aggregation", status: "ok", processed: nil, progress: 100))

        let elapsedMs = Int(Date().timeIntervalSince(start) * 1000)

        return SummaryResult(
            success: true,
            summary: finalSummary,
            error: nil,
            retryable: nil,
            stage: nil,
            warnings: warnings.isEmpty ? nil : warnings,
            stageResults: stageResults,
            mode: request.mode ?? "chunked",
            version: request.version ?? "1.0",
            elapsedMs: elapsedMs
        )
    }

    private static func runModel(
        prompt: Prompt,
        instructions: String,
        options: GenerationOptions,
        stage: String?
    ) async throws -> String {
        let session = LanguageModelSession(instructions: instructions)
        do {
            let response = try await session.respond(to: prompt, options: options)
            let trimmed = response.content.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !isPlaceholderResponse(trimmed) else {
                throw SummarizationFailure(message: placeholderMessage, stage: stage, retryable: true)
            }
            return trimmed
        } catch let error as LanguageModelSession.GenerationError {
            let message = generationErrorMessage(for: error)
            let retryable = isRetryable(error: error)
            throw SummarizationFailure(message: message, stage: stage, retryable: retryable)
        }
    }

    private static func runStructuredModel(
        prompt: Prompt,
        instructions: String,
        options: GenerationOptions,
        stage: String?
    ) async throws -> StructuredSummary {
        let session = LanguageModelSession(instructions: instructions)
        do {
            let response = try await session.respond(
                to: prompt,
                generating: StructuredSummary.self,
                options: options
            )
            let summary = response.content
            guard !summary.overall.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                throw SummarizationFailure(message: placeholderMessage, stage: stage, retryable: true)
            }
            return summary
        } catch let error as LanguageModelSession.GenerationError {
            let message = generationErrorMessage(for: error)
            let retryable = isRetryable(error: error)
            throw SummarizationFailure(message: message, stage: stage, retryable: retryable)
        }
    }

    private static func renderMarkdown(_ summary: StructuredSummary, note: String?) -> String {
        buildStructuredSummary(
            overall: summary.overall,
            takeaways: summary.keyTakeaways,
            actionItems: summary.actionItems,
            questions: summary.questions,
            note: note
        )
    }

    private static func decodeChunkedRequest(from data: Data) -> ChunkedSummarizationRequest? {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        if let request = try? decoder.decode(ChunkedSummarizationRequest.self, from: data) {
            if let mode = request.mode, mode.lowercased() == "chunked" {
                return request
            }
            if let chunks = request.chunks, !chunks.isEmpty {
                return request
            }
        }
        return nil
    }

    private static func buildAggregationPrompt(from summaries: [ChunkSummary], targetSentences: Int) -> String {
        let sections = summaries.sorted { $0.index < $1.index }
            .enumerated()
            .map { offset, element in
                "Section \(offset + 1): \(element.summary)"
            }
            .joined(separator: "\n\n")

        return """
The following are summaries of sections from a longer document.
Use them to produce the required Markdown summary format described in the instructions.

Section summaries:
\(sections)
"""
    }

    private static func availabilityMessage(for availability: SystemLanguageModel.Availability) -> String {
        switch availability {
        case .unavailable(.deviceNotEligible):
            return "Device not eligible for Apple Intelligence"
        case .unavailable(.appleIntelligenceNotEnabled):
            return "Apple Intelligence not enabled in Settings"
        case .unavailable(.modelNotReady):
            return "Language model not ready - may be downloading"
        default:
            return "Language model unavailable"
        }
    }

    private static func generationErrorMessage(for error: LanguageModelSession.GenerationError) -> String {
        switch error {
        case .exceededContextWindowSize:
            return "Content too long for processing"
        default:
            return "Generation failed: \(error.localizedDescription)"
        }
    }

    private static func isRetryable(error: LanguageModelSession.GenerationError) -> Bool { false }

    private static func isPlaceholderResponse(_ text: String) -> Bool {
        let lowered = text.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let patterns = [
            "please provide the text you would like summarized",
            "provide the text you'd like summarized",
            "provide the text you would like summarized",
            "please provide the text to summarize",
            "send the text you'd like summarized"
        ]
        return patterns.contains { lowered.contains($0) }
    }

    private static func fallbackChunkTakeaway(from text: String) -> String {
        let sentences = splitSentences(from: text)
        let excerpt = sentences.prefix(2)
        return excerpt.joined(separator: " ")
    }

    private static func fallbackSummary(from text: String, targetSentences: Int, note: String? = nil) -> String {
        let components = analyzeSentences(for: text, takeawaysLimit: 3)
        return buildStructuredSummary(
            overall: components.overall,
            takeaways: components.takeaways,
            actionItems: components.actionItems,
            questions: components.questions,
            note: note
        )
    }

    private static func fallbackSummary(fromChunks chunks: [ChunkSummary], targetSentences: Int, note: String? = nil) -> String {
        let combined = chunks.sorted { $0.index < $1.index }
            .map { $0.summary }
            .joined(separator: " ")
        return fallbackSummary(from: combined, targetSentences: targetSentences, note: note)
    }

    private static func analyzeSentences(for text: String, takeawaysLimit: Int) -> (overall: String, takeaways: [String], actionItems: [String], questions: [String]) {
        let sentences = splitSentences(from: text)
        guard let first = sentences.first else {
            return (
                overall: text.trimmingCharacters(in: .whitespacesAndNewlines),
                takeaways: [],
                actionItems: [],
                questions: []
            )
        }

        var remaining = Array(sentences.dropFirst())

        var questions = remaining.filter { $0.contains("?") }
        questions = Array(questions.prefix(3))
        remaining.removeAll { questions.contains($0) }

        let actionKeywords = [" should ", " need to ", " must ", " will ", " plan to ", " ensure ", " follow up", " schedule ", " consider ", " review "]
        var actions: [String] = []
        for sentence in remaining {
            if actionKeywords.contains(where: { sentence.lowercased().contains($0) }) {
                actions.append(sentence)
            }
            if actions.count == 3 {
                break
            }
        }
        remaining.removeAll { actions.contains($0) }

        let takeaways = Array(remaining.prefix(takeawaysLimit))

        return (
            overall: first,
            takeaways: takeaways,
            actionItems: actions,
            questions: questions
        )
    }

    private static func buildStructuredSummary(
        overall: String,
        takeaways: [String],
        actionItems: [String],
        questions: [String],
        note: String? = nil
    ) -> String {
        let formattedNote = note.map { "> _\($0)_\n\n" } ?? ""
        let formattedTakeaways = bulletList(from: takeaways)
        let formattedActions = bulletList(from: actionItems)
        let formattedQuestions = bulletList(from: questions)

        return """
\(formattedNote)**Overall:** \(overall)
### Key Takeaways
\(formattedTakeaways)
### Action Items
\(formattedActions)
### Questions
\(formattedQuestions)
""".trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func bulletList(from sentences: [String]) -> String {
        if sentences.isEmpty {
            return "- None"
        }
        return sentences.prefix(3)
            .map { "- \($0)" }
            .joined(separator: "\n")
    }

    private static func splitSentences(from text: String) -> [String] {
        var sentences: [String] = []
        var current = ""
        for character in text {
            current.append(character)
            if ".!?".contains(character) {
                let trimmed = current.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty {
                    sentences.append(trimmed)
                }
                current.removeAll(keepingCapacity: true)
            }
        }

        let trailing = current.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trailing.isEmpty {
            sentences.append(trailing)
        }

        return sentences
    }
}

// MARK: - Models

struct ChunkedSummarizationRequest: Decodable {
    let version: String?
    let mode: String?
    let contentFormat: String?
    let origin: String?
    let instructions: String?
    let chunks: [Chunk]?
    let strategy: Strategy?
}

struct Chunk: Decodable {
    let id: String?
    let index: Int?
    let text: String?
    let charLength: Int?
    let tokenEstimate: Int?
    let metadata: [String: MetadataValue]?

    var displayName: String {
        if let index {
            return "#\(index)"
        }
        if let id {
            return id
        }
        return "unknown"
    }
}

struct Strategy: Decodable {
    let type: String?
    let maxChunkChars: Int?
    let targetSummarySentences: Int?
    let language: String?
    let retryAttempt: Int?
}

struct MetadataValue: Decodable {
    let stringValue: String

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let string = try? container.decode(String.self) {
            stringValue = string
        } else if let int = try? container.decode(Int.self) {
            stringValue = String(int)
        } else if let double = try? container.decode(Double.self) {
            stringValue = String(double)
        } else if let bool = try? container.decode(Bool.self) {
            stringValue = bool ? "true" : "false"
        } else {
            stringValue = ""
        }
    }
}

struct ChunkSummary {
    let id: String
    let index: Int
    let summary: String
}

/// Structured summary produced via guided generation. The `@Generable` macro
/// builds a schema that the on-device model is constrained to fill, so the
/// returned object is always structurally valid — no prose parsing required.
@Generable
struct StructuredSummary {
    @Guide(description: "A single sentence capturing the core message of the content.")
    let overall: String

    @Guide(description: "The most important insights, at most three, each a concise fact-based phrase.")
    let keyTakeaways: [String]

    @Guide(description: "Concrete next steps, at most three. Empty if there are no clear actions.")
    let actionItems: [String]

    @Guide(description: "Open questions or uncertainties, at most three. Empty if there are none.")
    let questions: [String]
}

struct StageResult: Encodable {
    let stage: String
    let status: String
    let processed: Int?
    let progress: Int?
}

struct SummaryResult: Encodable {
    let success: Bool
    let summary: String?
    let error: String?
    let retryable: Bool?
    let stage: String?
    let warnings: [String]?
    let stageResults: [StageResult]?
    let mode: String?
    let version: String?
    let elapsedMs: Int?

    func toJSON() -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = []
        if let data = try? encoder.encode(self), let string = String(data: data, encoding: .utf8) {
            return string
        }
        return "{\"success\":false,\"error\":\"JSON encoding failed\"}"
    }
}

struct SummarizationFailure: Error {
    let message: String
    let stage: String?
    let retryable: Bool
    let stageResults: [StageResult]?

    init(message: String, stage: String?, retryable: Bool, stageResults: [StageResult]? = nil) {
        self.message = message
        self.stage = stage
        self.retryable = retryable
        self.stageResults = stageResults
    }

    func toResult() -> SummaryResult {
        SummaryResult(
            success: false,
            summary: nil,
            error: message,
            retryable: retryable,
            stage: stage,
            warnings: nil,
            stageResults: stageResults,
            mode: nil,
            version: nil,
            elapsedMs: nil
        )
    }
}
