import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    
    var body: some View {
        VStack(spacing: 0) {
            // 顶部状态栏
            HStack {
                Text("🟢 就绪")
                    .font(.system(size: 14, weight: .medium))
                Spacer()
                Text(Date(), style: .time)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color(NSColor.windowBackgroundColor))
            
            Divider()
            
            // 标签页
            TabView(selection: $selectedTab) {
                PositionView()
                    .tabItem { Label("持仓", systemImage: "chart.pie") }
                    .tag(0)
                
                WatchListView()
                    .tabItem { Label("自选股", systemImage: "star") }
                    .tag(1)
                
                TradeHistoryView()
                    .tabItem { Label("交易记录", systemImage: "list.bullet") }
                    .tag(2)
                
                LogView()
                    .tabItem { Label("日志", systemImage: "doc.text") }
                    .tag(3)
            }
            .padding(.top, 8)
            
            Divider()
            
            // 底部按钮栏
            HStack {
                Button(action: {
                    NotificationCenter.default.post(name: .refreshPrices, object: nil)
                }) {
                    Label("刷新价格", systemImage: "arrow.clockwise")
                }
                .buttonStyle(.bordered)
                
                Button(action: {
                    NotificationCenter.default.post(name: .showBuyDialog, object: nil)
                }) {
                    Label("买入", systemImage: "arrow.up.circle")
                }
                .buttonStyle(.bordered)
                .tint(.green)
                
                Button(action: {
                    NotificationCenter.default.post(name: .showSellDialog, object: nil)
                }) {
                    Label("卖出", systemImage: "arrow.down.circle")
                }
                .buttonStyle(.bordered)
                .tint(.red)
                
                Spacer()
                
                Button(action: {
                    NotificationCenter.default.post(name: .toggleMonitoring, object: nil)
                }) {
                    Label("开始监控", systemImage: "play.fill")
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(12)
        }
        .frame(minWidth: 600, minHeight: 400)
    }
}

// 通知名称扩展
extension Notification.Name {
    static let refreshPrices = Notification.Name("refreshPrices")
    static let showBuyDialog = Notification.Name("showBuyDialog")
    static let showSellDialog = Notification.Name("showSellDialog")
    static let toggleMonitoring = Notification.Name("toggleMonitoring")
}

#Preview {
    ContentView()
}
