import SwiftUI

struct WatchListView: View {
    @ObservedObject var service = StockService.shared
    @State private var showingAddSheet = false
    @State private var newCode = ""
    @State private var newName = ""
    
    var body: some View {
        VStack(spacing: 0) {
            // 工具栏
            HStack {
                Button(action: { showingAddSheet = true }) {
                    Label("添加", systemImage: "plus")
                }
                .buttonStyle(.bordered)
                
                Button(action: {
                    let selected = service.stocks.indices
                    service.removeStock(at: IndexSet(selected))
                }) {
                    Label("删除", systemImage: "minus")
                }
                .buttonStyle(.bordered)
                
                Button(action: {
                    NotificationCenter.default.post(name: .refreshPrices, object: nil)
                }) {
                    Label("刷新", systemImage: "arrow.clockwise")
                }
                .buttonStyle(.bordered)
                
                Spacer()
            }
            .padding(8)
            
            Divider()
            
            // 表格
            if service.stocks.isEmpty {
                VStack {
                    Image(systemName: "star")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("暂无自选股")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(service.stocks) {
                    TableColumn("股票代码") { stock in
                        Text(stock.code)
                    }
                    .width(80)
                    
                    TableColumn("股票名称") { stock in
                        Text(stock.name)
                    }
                    .width(100)
                    
                    TableColumn("当前价") { stock in
                        Text(stock.price)
                    }
                    .width(70)
                    
                    TableColumn("涨跌") { stock in
                        Text(stock.change)
                            .foregroundColor(stock.change.hasPrefix("+") ? .red : (stock.change.hasPrefix("-") ? .green : .primary))
                    }
                    .width(60)
                    
                    TableColumn("涨跌幅%") { stock in
                        Text(stock.changePercent)
                            .foregroundColor(stock.changePercent.hasPrefix("+") ? .red : (stock.changePercent.hasPrefix("-") ? .green : .primary))
                    }
                    .width(80)
                    
                    TableColumn("MA5") { stock in
                        Text(stock.ma5)
                    }
                    .width(60)
                    
                    TableColumn("MA20") { stock in
                        Text(stock.ma20)
                    }
                    .width(60)
                    
                    TableColumn("状态") { stock in
                        Text(stock.signal)
                    }
                    .width(80)
                }
            }
        }
        .sheet(isPresented: $showingAddSheet) {
            AddStockSheet(isPresented: $showingAddSheet)
        }
    }
}

struct AddStockSheet: View {
    @Binding var isPresented: Bool
    @ObservedObject var service = StockService.shared
    
    @State private var code = ""
    @State private var name = ""
    
    var body: some View {
        VStack(spacing: 16) {
            Text("添加自选股")
                .font(.headline)
            
            TextField("股票代码", text: $code)
                .textFieldStyle(.roundedBorder)
            
            TextField("股票名称", text: $name)
                .textFieldStyle(.roundedBorder)
            
            HStack {
                Button("取消") {
                    isPresented = false
                }
                .buttonStyle(.bordered)
                
                Button("添加") {
                    if !code.isEmpty && !name.isEmpty {
                        service.addStock(Stock(code: code, name: name))
                        isPresented = false
                    }
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(20)
        .frame(width: 300)
    }
}

#Preview {
    WatchListView()
}
