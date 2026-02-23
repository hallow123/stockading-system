import SwiftUI

struct TradeHistoryView: View {
    @ObservedObject var service = StockService.shared
    
    var body: some View {
        VStack(spacing: 0) {
            if service.trades.isEmpty {
                VStack {
                    Image(systemName: "list.bullet")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("暂无交易记录")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(service.trades) {
                    TableColumn("时间") { trade in
                        Text(trade.time)
                    }
                    .width(100)
                    
                    TableColumn("股票代码") { trade in
                        Text(trade.code)
                    }
                    .width(80)
                    
                    TableColumn("股票名称") { trade in
                        Text(trade.name)
                    }
                    .width(100)
                    
                    TableColumn("方向") { trade in
                        HStack {
                            Image(systemName: trade.direction == "buy" ? "arrow.up" : "arrow.down")
                            Text(trade.direction == "buy" ? "买入" : "卖出")
                        }
                        .foregroundColor(trade.direction == "buy" ? .red : .green)
                    }
                    .width(60)
                    
                    TableColumn("价格") { trade in
                        Text(String(format: "%.2f", trade.price))
                    }
                    .width(70)
                    
                    TableColumn("数量") { trade in
                        Text("\(trade.quantity)")
                    }
                    .width(60)
                    
                    TableColumn("状态") { trade in
                        Text(trade.status)
                    }
                    .width(80)
                }
            }
        }
    }
}

#Preview {
    TradeHistoryView()
}
