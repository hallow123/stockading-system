import SwiftUI

struct LogView: View {
    @ObservedObject var service = StockService.shared
    @State private var autoScroll = true
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Toggle("自动滚动", isOn: $autoScroll)
                    .toggleStyle(.checkbox)
                
                Spacer()
                
                Button(action: {
                    service.logs.removeAll()
                }) {
                    Label("清空", systemImage: "trash")
                }
                .buttonStyle(.bordered)
            }
            .padding(8)
            
            Divider()
            
            if service.logs.isEmpty {
                VStack {
                    Image(systemName: "doc.text")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("暂无日志")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 4) {
                            ForEach(service.logs) { log in
                                HStack(alignment: .top) {
                                    Text("[\(log.timestamp)]")
                                        .font(.system(size: 11, design: .monospaced))
                                        .foregroundColor(.secondary)
                                    Text(log.message)
                                        .font(.system(size: 12, design: .monospaced))
                                }
                                .id(log.id)
                            }
                        }
                        .padding(8)
                    }
                    .onChange(of: service.logs.count) { _, _ in
                        if autoScroll, let firstLog = service.logs.first {
                            withAnimation {
                                proxy.scrollTo(firstLog.id, anchor: .top)
                            }
                        }
                    }
                }
            }
        }
    }
}

#Preview {
    LogView()
}
