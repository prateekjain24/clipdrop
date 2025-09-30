import Foundation
import FoundationModels

@main
struct ClipdropSummarizeApp {
    private static let defaultInstructions = """
You are a helpful assistant that creates concise summaries.
Summarize the provided text in 2-4 sentences, focusing on key points and main ideas.
Keep the summary clear and informative.
"""

    private static let chunkInstructions = """
You summarize long documents by first summarizing each section and then combining the results.
For each section you receive, produce a short paragraph capturing the essential points in plain language.
Stay factual and avoid speculation.
"""

    private static let aggregationHint = """
Combine the section summaries into a cohesive overview.
Highlight the main themes and outcomes in a concise form.
Target NUMBER_SENTENCES sentences.
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

        let summary = try await runModel(
            prompt: Prompt("Summarize this text:\n\n\(trimmed)"),
            instructions: defaultInstructions,
            options: GenerationOptions(
                sampling: nil,
                temperature: 0.3,
                maximumResponseTokens: 200
            ),
            stage: nil
        )

        return SummaryResult(
            success: true,
            summary: summary,
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
        let aggregationOptions = GenerationOptions(
            sampling: nil,
            temperature: 0.3,
            maximumResponseTokens: 240
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
                if failure.message == placeholderMessage {
                    let fallback = fallbackSummary(from: snippet, targetSentences: 2)
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
        let aggregationPrompt = buildAggregationPrompt(from: chunkSummaries, targetSentences: targetSentences)

        let aggregateInstructions: String
        if let custom = request.instructions, !custom.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            aggregateInstructions = custom + "\n" + aggregationHint.replacingOccurrences(of: "NUMBER_SENTENCES", with: "\(targetSentences)")
        } else {
            aggregateInstructions = defaultInstructions + "\n" + aggregationHint.replacingOccurrences(of: "NUMBER_SENTENCES", with: "\(targetSentences)")
        }

        let finalSummary: String
        do {
            finalSummary = try await runModel(
                prompt: Prompt(aggregationPrompt),
                instructions: aggregateInstructions,
                options: aggregationOptions,
                stage: "aggregation"
            )
        } catch let failure as SummarizationFailure {
            if failure.message == placeholderMessage {
                let fallback = fallbackSummary(fromChunks: chunkSummaries, targetSentences: targetSentences)
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
Combine them into a cohesive summary of the overall content. Use approximately \(targetSentences) sentences.

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

    private static func fallbackSummary(from text: String, targetSentences: Int) -> String {
        extractSentences(from: text, limit: targetSentences)
    }

    private static func fallbackSummary(fromChunks chunks: [ChunkSummary], targetSentences: Int) -> String {
        let combined = chunks.sorted { $0.index < $1.index }
            .map { $0.summary }
            .joined(separator: " ")
        return extractSentences(from: combined, limit: targetSentences)
    }

    private static func extractSentences(from text: String, limit: Int) -> String {
        guard limit > 0 else { return "" }

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
                if sentences.count >= limit {
                    break
                }
            }
        }

        if sentences.count < limit {
            let trimmed = current.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                sentences.append(trimmed)
            }
        }

        return sentences.prefix(limit).joined(separator: " ")
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
