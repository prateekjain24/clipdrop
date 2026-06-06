import Foundation
import FoundationModels

// clipdrop-suggest-name — propose a short descriptive title for a file based
// on its content, using the on-device model via guided generation. Reads the
// content from stdin and prints JSON: {"success": true, "title": "..."}.
//
// The Python caller slugifies the title into a filesystem-safe name, so this
// helper only needs to return a clean human-readable title.

@main
struct ClipdropSuggestNameApp {
    private static let instructions = """
You generate a short, descriptive title for a file based on its content. The title should be three to eight words in Title Case capturing the main topic. Do not include a file extension, quotes, dates, or punctuation beyond spaces. Never ask the user for more text.
"""

    @Generable
    struct SuggestedName {
        @Guide(description: "A concise three-to-eight word descriptive title in Title Case, no punctuation or file extension.")
        let title: String
    }

    static func main() async {
        let data = FileHandle.standardInput.readDataToEndOfFile()
        let text = (String(data: data, encoding: .utf8) ?? "")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard !text.isEmpty else {
            emit(success: false, title: nil, error: "Content is empty")
        }

        let model = SystemLanguageModel.default
        guard case .available = model.availability else {
            emit(success: false, title: nil, error: "Language model unavailable")
        }

        // Only the opening of the content is needed to name it.
        let snippet = String(text.prefix(4000))

        do {
            let session = LanguageModelSession(instructions: instructions)
            let response = try await session.respond(
                to: Prompt("Suggest a filename title for the following content:\n\n\(snippet)"),
                generating: SuggestedName.self,
                options: GenerationOptions(
                    sampling: nil,
                    temperature: 0.2,
                    maximumResponseTokens: 40
                )
            )
            let title = response.content.title.trimmingCharacters(in: .whitespacesAndNewlines)
            if title.isEmpty {
                emit(success: false, title: nil, error: "Model returned an empty title")
            } else {
                emit(success: true, title: title, error: nil)
            }
        } catch {
            emit(success: false, title: nil, error: "Generation failed: \(error.localizedDescription)")
        }
    }

    private static func emit(success: Bool, title: String?, error: String?) -> Never {
        var object: [String: Any] = ["success": success]
        if let title { object["title"] = title }
        if let error { object["error"] = error }

        if let data = try? JSONSerialization.data(withJSONObject: object),
           let json = String(data: data, encoding: .utf8) {
            print(json)
        } else {
            print("{\"success\":false,\"error\":\"JSON encoding failed\"}")
        }
        exit(success ? 0 : 1)
    }
}
