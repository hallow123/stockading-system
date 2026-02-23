import SwiftUI

struct PositionView: View {
    @ObservedObject var service = StockService.shared
    
    var body: some View {
        VStack(spacing: 0) {
            if service.positions.isEmpty {
                VStack {
                    Image(systemName: "chart.pie")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("暂无持仓")
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(service.positions) {
                    TableColumn("股票代码") { position in
                        Text(position.code)
                    }
                    .width(80)
                    
                    TableColumn("股票名称") { position in
                        Text(position.name)
                    }
                    .width(100)
                    
                    TableColumn("持仓量") { position in
                        Text("\(position.quantity)")
                    }
                    .width(60)
                    
                    TableColumn("成本价") { position in
                        Text(String(format: "%.2f", position.costPrice))
                    }
                    .width(70)
                    
                    TableColumn("当前价") { position in
                        Text(String(format: "%.2f", position.currentPrice))
                    }
                    .width(70)
                    
                    TableColumn("盈亏") { position in
                        Text(String(format: "%.2f", position.profit))
                            .foregroundColor(position.profit >= 0 ? .red : .green)
                    }
                    .width(80)
                    
                    TableColumn("盈亏%") { position in
                        Text(String(format: "%.2f%%", position.profitPercent))
                            .foregroundColor(position.profitPercent >= 0 ? .red : .green)
                    }
                    .width(80)
                }
            }
        }
    }
}

#Preview {
    PositionView()
}
