import SwiftUI

struct TradeDialogView: View {
    let isBuy: Bool
    @Binding var isPresented: Bool
    @ObservedObject var service = StockService.shared
    
    @State private var code = ""
    @State private var name = ""
    @State private var price = ""
    @State private var quantity = ""
    @State private var isExecuting = false
    @State private var resultMessage = ""
    
    var body: some View {
        VStack(spacing: 16) {
            Text(isBuy ? "买入股票" : "卖出股票")
                .font(.headline)
            
            TextField("股票代码", text: $code)
                .textFieldStyle(.roundedBorder)
                .frame(width: 250)
            
            TextField("股票名称", text: $name)
                .textFieldStyle(.roundedBorder)
                .frame(width: 250)
            
            TextField("价格", text: $price)
                .textFieldStyle(.roundedBorder)
                .frame(width: 250)
            
            TextField(isBuy ? "数量(100的整数倍)" : "数量(填0为全部)", text: $quantity)
                .textFieldStyle(.roundedBorder)
                .frame(width: 250)
            
            if !resultMessage.isEmpty {
                Text(resultMessage)
                    .foregroundColor(resultMessage.hasPrefix("✅") ? .green : .red)
                    .font(.system(size: 13))
            }
            
            HStack {
                Button("取消") {
                    isPresented = false
                }
                .buttonStyle(.bordered)
                
                Button(action: executeTrade) {
                    if isExecuting {
                        ProgressView()
                            .scaleEffect(0.8)
                    } else {
                        Text(isBuy ? "执行买入" : "执行卖出")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isExecuting || code.isEmpty || name.isEmpty || price.isEmpty || quantity.isEmpty)
            }
        }
        .padding(20)
        .frame(width: 320)
    }
    
    private func executeTrade() {
        guard let priceValue = Double(price),
              let quantityValue = Int(quantity) else {
            resultMessage = "❌ 请输入有效的价格和数量"
            return
        }
        
        if isBuy && quantityValue % 100 != 0 {
            resultMessage = "❌ 数量必须是100的整数倍"
            return
        }
        
        isExecuting = true
        resultMessage = "⏳ 正在执行..."
        
        if isBuy {
            service.buyStock(code: code, name: name, price: priceValue, quantity: quantityValue) { success in
                isExecuting = false
                resultMessage = success ? "✅ 买入成功!" : "❌ 买入失败"
                if success {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                        isPresented = false
                    }
                }
            }
        } else {
            service.sellStock(code: code, name: name, price: priceValue, quantity: quantityValue) { success in
                isExecuting = false
                resultMessage = success ? "✅ 卖出成功!" : "❌ 卖出失败"
                if success {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                        isPresented = false
                    }
                }
            }
        }
    }
}

#Preview {
    TradeDialogView(isBuy: true, isPresented: .constant(true))
}
