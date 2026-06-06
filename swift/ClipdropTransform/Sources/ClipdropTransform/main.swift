import Foundation
import FoundationModels

// clipdrop-transform — apply an on-device transformation to clipboard text.
//
// Reads a JSON request from stdin and prints a JSON response to stdout:
//
//   request:  {"operation":"rewrite","content":"...","style":"formal"}
//             {"operation":"prompt","content":"...","instruction":"..."}
//             {"operation":"table","content":"..."}
//
//   response: {"success":true,"result":"<text>"}                 (rewrite/prompt)
//             {"success":true,"table":{"headers":[...],"rows":[[...]]}}  (table)
//             {"success":false,"error":"..."}
//
// rewrite/prompt are plain text-to-text generation; table uses guided
// generation so the structure is guaranteed.

@main
struct ClipdropTransformApp {
    private static let rewriteInstructions = """
You rewrite text in a requested style while preserving its meaning and key facts. Output only the rewritten text, with no preamble, explanation, or surrounding quotation marks.
"""

    private static let promptInstructions = """
You transform text according to the user's instruction. Apply the instruction faithfully and output only the resulting text, with no preamble or commentary.
"""

    private static let tableInstructions = """
You convert unstructured text into a clean table. Choose concise, descriptive column headers and put one record per row, with each row's cells aligned to the headers in order. Keep cell values short. Never invent data that is not present in the source.
"""

    static func main() async {
        let data = FileHandle.standardInput.readDataToEndOfFile()

        guard let request = try? JSONDecoder().decode(TransformRequest.self, from: data) else {
            emit(success: false, error: "Invalid transform request")
        }

        let content = request.content.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !content.isEmpty else {
            emit(success: false, error: "Content is empty")
        }

        let model = SystemLanguageModel.default
        guard case .available = model.availability else {
            emit(success: false, error: availabilityMessage(for: model.availability))
        }

        do {
            switch request.operation {
            case "rewrite":
                let style = request.style?.trimmingCharacters(in: .whitespacesAndNewlines)
                let descriptor = (style?.isEmpty == false) ? style! : "clear and concise"
                let text = try await runText(
                    instructions: rewriteInstructions,
                    prompt: "Rewrite the following text to be \(descriptor).\n\nText:\n\(content)"
                )
                emitResult(text)

            case "prompt":
                let instruction = request.instruction?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                guard !instruction.isEmpty else {
                    emit(success: false, error: "Missing instruction for prompt operation")
                }
                let text = try await runText(
                    instructions: promptInstructions,
                    prompt: "Instruction: \(instruction)\n\nText:\n\(content)"
                )
                emitResult(text)

            case "table":
                let table = try await runTable(content: content)
                emitTable(table)

            default:
                emit(success: false, error: "Unknown operation: \(request.operation)")
            }
        } catch let failure as TransformError {
            emit(success: false, error: failure.message)
        } catch {
            emit(success: false, error: "Transform failed: \(error.localizedDescription)")
        }
    }

    // MARK: - Generation

    private static func runText(instructions: String, prompt: String) async throws -> String {
        let session = LanguageModelSession(instructions: instructions)
        do {
            let response = try await session.respond(
                to: Prompt(prompt),
                options: GenerationOptions(
                    sampling: nil,
                    temperature: 0.3,
                    maximumResponseTokens: 2000
                )
            )
            let text = response.content.trimmingCharacters(in: .whitespacesAndNewlines)
            if text.isEmpty {
                throw TransformError(message: "Model returned empty output")
            }
            return text
        } catch let error as LanguageModelSession.GenerationError {
            throw TransformError(message: generationErrorMessage(for: error))
        }
    }

    private static func runTable(content: String) async throws -> GeneratedTable {
        let session = LanguageModelSession(instructions: tableInstructions)
        do {
            let response = try await session.respond(
                to: Prompt("Convert the following text into a table.\n\n\(content)"),
                generating: GeneratedTable.self,
                options: GenerationOptions(
                    sampling: nil,
                    temperature: 0.2,
                    maximumResponseTokens: 1500
                )
            )
            let table = response.content
            if table.headers.isEmpty && table.rows.isEmpty {
                throw TransformError(message: "Could not extract a table from the content")
            }
            return table
        } catch let error as LanguageModelSession.GenerationError {
            throw TransformError(message: generationErrorMessage(for: error))
        }
    }

    // MARK: - Output

    private static func emitResult(_ text: String) -> Never {
        emitJSON(["success": true, "result": text])
    }

    private static func emitTable(_ table: GeneratedTable) -> Never {
        let rows = table.rows.map { $0.cells }
        emitJSON([
            "success": true,
            "table": ["headers": table.headers, "rows": rows],
        ])
    }

    private static func emit(success: Bool, error: String) -> Never {
        emitJSON(["success": success, "error": error])
    }

    private static func emitJSON(_ object: [String: Any]) -> Never {
        let success = (object["success"] as? Bool) ?? false
        if let data = try? JSONSerialization.data(withJSONObject: object),
           let json = String(data: data, encoding: .utf8) {
            print(json)
        } else {
            print("{\"success\":false,\"error\":\"JSON encoding failed\"}")
        }
        exit(success ? 0 : 1)
    }

    // MARK: - Helpers

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
            return "Content too long to transform"
        default:
            return "Generation failed: \(error.localizedDescription)"
        }
    }
}

// MARK: - Models

struct TransformRequest: Decodable {
    let operation: String
    let content: String
    let style: String?
    let instruction: String?
    let language: String?
}

@Generable
struct GeneratedTable {
    @Guide(description: "Concise, descriptive column header names for the table.")
    let headers: [String]

    @Guide(description: "The table rows; each row's cells align with the headers in order.")
    let rows: [TableRow]
}

@Generable
struct TableRow {
    @Guide(description: "The cell values for this row, one per column, in header order.")
    let cells: [String]
}

struct TransformError: Error {
    let message: String
}
