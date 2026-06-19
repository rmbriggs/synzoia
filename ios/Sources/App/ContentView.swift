import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "moon.stars.fill")
                .font(.system(size: 48))
            Text("synzoia")
                .font(.largeTitle.bold())
        }
    }
}

#Preview {
    ContentView()
}
