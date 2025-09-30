import Foundation
import FoundationModels

@main
struct ClipdropSummarizeApp {
    static func main() async {
        let systemModel = SystemLanguageModel.default
        guard case .available = systemModel.availability else {
            printError(availability: systemModel.availability)
            exit(1)
        }

        let inputData = FileHandle.standardInput.readDataToEndOfFile()
        guard let inputText = String(data: inputData, encoding: .utf8) else {
            printError(message: "Invalid input encoding")
            exit(1)
        }

        guard inputText.count <= 15_000 else {
            printError(message: "Content too long for summarization")
            exit(1)
        }

        do {
            let instructions = """
            You are a helpful assistant that creates concise summaries.
            Summarize the provided text in 2-4 sentences, focusing on key points and main ideas.
            Keep the summary clear and informative.
            """

            let session = LanguageModelSession(instructions: instructions)
            let options = GenerationOptions(
                sampling: nil,
                temperature: 0.3,
                maximumResponseTokens: 200
            )

            let prompt = Prompt("Summarize this text: \(inputText)")
            let response = try await session.respond(to: prompt, options: options)
            let summaryText = response.content

            let result = SummaryResult(summary: summaryText, success: true)
            print(result.toJSON())
        } catch let error as LanguageModelSession.GenerationError {
            printError(generationError: error)
            exit(1)
        } catch {
            printError(message: "Unexpected error: \(error)")
            exit(1)
        }
    }

    private static func printError(availability: SystemLanguageModel.Availability) {
        let message = switch availability {
        case .unavailable(.deviceNotEligible):
            "Device not eligible for Apple Intelligence"
        case .unavailable(.appleIntelligenceNotEnabled):
            "Apple Intelligence not enabled in Settings"
        case .unavailable(.modelNotReady):
            "Language model not ready - may be downloading"
        default:
            "Language model unavailable"
        }
        let error = SummaryResult(error: message, success: false)
        print(error.toJSON())
    }

    private static func printError(generationError: LanguageModelSession.GenerationError) {
        let message = switch generationError {
        case .exceededContextWindowSize(_):
            "Content too long for processing"
        default:
            "Generation failed: \(generationError.localizedDescription)"
        }
        let error = SummaryResult(error: message, success: false)
        print(error.toJSON())
    }

    private static func printError(message: String) {
        let error = SummaryResult(error: message, success: false)
        print(error.toJSON())
    }
}

struct SummaryResult {
    let summary: String?
    let error: String?
    let success: Bool

    init(summary: String, success: Bool) {
        self.summary = summary
        self.error = nil
        self.success = success
    }

    init(error: String, success: Bool) {
        self.summary = nil
        self.error = error
        self.success = success
    }

    func toJSON() -> String {
        let payload: [String: Any] = [
            "success": success,
            "summary": summary ?? NSNull(),
            "error": error ?? NSNull()
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: payload),
              let jsonString = String(data: jsonData, encoding: .utf8) else {
            return "{\"error\":\"JSON encoding failed\",\"success\":false}"
        }
        return jsonString
    }
}
