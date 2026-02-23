import Foundation
import SwiftUI

class StockService: ObservableObject {
    static let shared = StockService()
    
    @Published var stocks: [Stock] = []
    @Published var positions: [Position] = []
    @Published var trades: [Trade] = []
    @Published var logs: [LogEntry] = []
    @Published var isMonitoring: Bool = false
    
    private let scriptsPath: String
    private var monitorTimer: Timer?
    
    init() {
        // 获取脚本目录 - 在 App bundle 中查找 Resources/Scripts
        if let bundlePath = Bundle.main.path(forResource: "Scripts", ofType: nil) {
            self.scriptsPath = bundlePath
        } else {
            // 开发时使用原始路径
            self.scriptsPath = "/Users/wangmaofu/Desktop/股票自动化交易系统/scripts"
        }
        
        loadData()
        setupNotificationObservers()
    }
    
    private func setupNotificationObservers() {
        NotificationCenter.default.addObserver(forName: .refreshPrices, object: nil, queue: .main) { _ in
            self.refreshPrices()
        }
        
        NotificationCenter.default.addObserver(forName: .toggleMonitoring, object: nil, queue: .main) { _ in
            if self.isMonitoring {
                self.stopMonitoring()
            } else {
                self.startMonitoring()
            }
        }
    }
    
    // MARK: - 数据加载
    
    func loadData() {
        loadStocks()
        loadPositions()
        loadTrades()
    }
    
    func loadStocks() {
        let filePath = "/Users/wangmaofu/Desktop/股票自动化交易系统/data/stocks.json"
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: filePath)),
              let loaded = try? JSONDecoder().decode([Stock].self, from: data) else {
            // 使用默认自选股
            stocks = [
                Stock(code: "002339", name: "积成电子"),
                Stock(code: "002237", name: "恒邦股份"),
                Stock(code: "601166", name: "兴业银行")
            ]
            return
        }
        stocks = loaded
    }
    
    func loadPositions() {
        let filePath = "/Users/wangmaofu/Desktop/股票自动化交易系统/data/positions.json"
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: filePath)),
              let loaded = try? JSONDecoder().decode([Position].self, from: data) else {
            positions = []
            return
        }
        positions = loaded
    }
    
    func loadTrades() {
        let filePath = "/Users/wangmaofu/Desktop/股票自动化交易系统/data/trades.json"
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: filePath)),
              let loaded = try? JSONDecoder().decode([Trade].self, from: data) else {
            trades = []
            return
        }
        trades = loaded
    }
    
    // MARK: - 价格刷新
    
    func refreshPrices() {
        addLog("🔄 正在刷新价格...")
        
        for i in stocks.indices {
            let code = stocks[i].code
            if let priceData = fetchPrice(for: code) {
                DispatchQueue.main.async {
                    self.stocks[i].price = priceData.price
                    self.stocks[i].change = priceData.change
                    self.stocks[i].changePercent = priceData.changePercent
                }
                addLog("📊 \(code): \(priceData.price)元 \(priceData.changePercent)")
            }
        }
        
        addLog("✅ 价格刷新完成")
    }
    
    private func fetchPrice(for code: String) -> (price: String, change: String, changePercent: String)? {
        // 调用 Python 脚本获取价格
        let scriptPath = "\(scriptsPath)/tonghuashun.py"
        let process = Process()
        let pipe = Pipe()
        
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = ["-c", "import sys; sys.path.insert(0, '\(scriptsPath)'); from tonghuashun import TonghuashunFetcher; print(TonghuashunFetcher().fetch_price('\(code)'))"]
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice
        
        do {
            try process.run()
            process.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            if let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
               !output.isEmpty && output != "None" {
                // 解析返回的价格数据
                if let data = output.data(using: .utf8),
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: String] {
                    return (json["price"] ?? "--", json["change"] ?? "--", json["change_percent"] ?? "--")
                }
            }
        } catch {
            addLog("⚠️ \(code) 价格获取失败: \(error.localizedDescription)")
        }
        
        return nil
    }
    
    // MARK: - 交易操作
    
    func buyStock(code: String, name: String, price: Double, quantity: Int, completion: @escaping (Bool) -> Void) {
        addLog("⏳ 执行买入: \(name)(\(code)) \(quantity)股 @ \(price)元")
        
        DispatchQueue.global().async {
            let process = Process()
            let pipe = Pipe()
            
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = ["-c", "import sys; sys.path.insert(0, '\(self.scriptsPath)'); from trade_executor import TradeExecutor; print(TradeExecutor().execute_buy('\(code)', '\(name)', \(price), \(quantity)))"]
            process.standardOutput = pipe
            process.standardError = FileHandle.nullDevice
            
            do {
                try process.run()
                process.waitUntilExit()
                
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                let success = output.lowercased().contains("true") || output == "True"
                
                DispatchQueue.main.async {
                    if success {
                        self.addLog("✅ 买入成功: \(name)(\(code))")
                    } else {
                        self.addLog("❌ 买入失败: \(output)")
                    }
                    completion(success)
                }
            } catch {
                DispatchQueue.main.async {
                    self.addLog("❌ 买入异常: \(error.localizedDescription)")
                    completion(false)
                }
            }
        }
    }
    
    func sellStock(code: String, name: String, price: Double, quantity: Int, completion: @escaping (Bool) -> Void) {
        addLog("⏳ 执行卖出: \(name)(\(code)) \(quantity)股 @ \(price)元")
        
        DispatchQueue.global().async {
            let process = Process()
            let pipe = Pipe()
            
            process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            process.arguments = ["-c", "import sys; sys.path.insert(0, '\(self.scriptsPath)'); from trade_executor import TradeExecutor; print(TradeExecutor().execute_sell('\(code)', '\(name)', \(price), \(quantity)))"]
            process.standardOutput = pipe
            process.standardError = FileHandle.nullDevice
            
            do {
                try process.run()
                process.waitUntilExit()
                
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                let success = output.lowercased().contains("true") || output == "True"
                
                DispatchQueue.main.async {
                    if success {
                        self.addLog("✅ 卖出成功: \(name)(\(code))")
                    } else {
                        self.addLog("❌ 卖出失败: \(output)")
                    }
                    completion(success)
                }
            } catch {
                DispatchQueue.main.async {
                    self.addLog("❌ 卖出异常: \(error.localizedDescription)")
                    completion(false)
                }
            }
        }
    }
    
    // MARK: - 监控
    
    func startMonitoring() {
        guard !isMonitoring else { return }
        isMonitoring = true
        addLog("🔴 开始自动监控...")
        
        // 每5分钟检查一次
        monitorTimer = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { _ in
            self.checkSignals()
        }
    }
    
    func stopMonitoring() {
        isMonitoring = false
        monitorTimer?.invalidate()
        monitorTimer = nil
        addLog("🟢 已停止监控")
    }
    
    private func checkSignals() {
        addLog("🔍 检查交易信号...")
        // TODO: 实现信号检查逻辑
    }
    
    // MARK: - 日志
    
    func addLog(_ message: String) {
        DispatchQueue.main.async {
            let entry = LogEntry(message: message)
            self.logs.insert(entry, at: 0)
            // 保留最近100条
            if self.logs.count > 100 {
                self.logs = Array(self.logs.prefix(100))
            }
        }
    }
    
    // MARK: - 自选股管理
    
    func addStock(_ stock: Stock) {
        stocks.append(stock)
        saveStocks()
        addLog("➕ 已添加自选股: \(stock.name)(\(stock.code))")
    }
    
    func removeStock(at offsets: IndexSet) {
        let removed = offsets.map { stocks[$0] }
        stocks.remove(atOffsets: offsets)
        saveStocks()
        for stock in removed {
            addLog("➖ 已删除自选股: \(stock.name)(\(stock.code))")
        }
    }
    
    private func saveStocks() {
        let filePath = "/Users/wangmaofu/Desktop/股票自动化交易系统/data/stocks.json"
        if let data = try? JSONEncoder().encode(stocks) {
            try? data.write(to: URL(fileURLWithPath: filePath))
        }
    }
}
