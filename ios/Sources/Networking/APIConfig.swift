import Foundation

struct APIConfig {
    let baseURL: URL

    static let production = APIConfig(baseURL: URL(string: "https://synzoia.vercel.app")!)
}
