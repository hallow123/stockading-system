import Foundation

struct Stock: Identifiable, Codable {
    var id: String { code }
    let code: String
    let name: String
    var price: String
    var change: String
    var changePercent: String
    var ma5: String
    var ma20: String
    var signal: String
    
    init(code: String, name: String, price: String = "--", change: String = "--", changePercent: String = "--", ma5: String = "--", ma20: String = "--", signal: String = "🟡 观察") {
        self.code = code
        self.name = name
        self.price = price
        self.change = change
        self.changePercent = changePercent
        self.ma5 = ma5
        self.ma20 = ma20
        self.signal = signal
    }
}

struct Position: Identifiable, Codable {
    var id: String { code }
    let code: String
    let name: String
    let quantity: Int
    let costPrice: Double
    var currentPrice: Double
    
    var profit: Double {
        (currentPrice - costPrice) * Double(quantity)
    }
    
    var profitPercent: Double {
        guard costPrice > 0 else { return 0 }
        return ((currentPrice / costPrice) - 1) * 100
    }
}

struct Trade: Identifiable, Codable {
    var id: String { "\(time)_\(code)" }
    let time: String
    let code: String
    let name: String
    let direction: String // "buy" or "sell"
    let price: Double
    let quantity: Int
    let status: String
}

struct LogEntry: Identifiable {
    var id: String { "\(timestamp)_\(message)" }
    let timestamp: String
    let message: String
    
    init(timestamp: String = "", message: String) {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss"
        self.timestamp = timestamp.isEmpty ? formatter.string(from: Date()) : timestamp
        self.message = message
    }
}
