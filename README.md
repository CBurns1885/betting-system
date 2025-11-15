# Betfair Arbitrage Trading Bot

A real-time automated trading system that monitors Betfair markets for arbitrage opportunities and executes trades automatically.

## ⚠️ Important Disclaimer

This software is for educational purposes only. Trading and betting involves significant financial risk. You are solely responsible for any financial losses incurred. Always:
- Test thoroughly with small stakes first
- Understand the risks involved
- Comply with all applicable laws and regulations
- Never bet more than you can afford to lose

## Features

- **Real-time Market Monitoring**: Continuously polls Betfair markets for price updates
- **Arbitrage Detection**: Automatically identifies profitable arbitrage opportunities
- **Automated Trading**: Places back and lay bets to lock in guaranteed profits
- **Risk Management**: Configurable stake limits, profit thresholds, and concurrent trade limits
- **Session Management**: Automatic authentication and session keep-alive
- **Comprehensive Logging**: Detailed logs of all trading activity
- **Error Handling**: Robust error handling with partial trade detection

## Architecture

```
src/
├── auth.ts                 # Betfair authentication (login, session management)
├── betfair-client.ts       # JSON-RPC API client
├── market-monitor.ts       # Real-time market data polling
├── order-manager.ts        # Order placement and validation
├── arbitrage-executor.ts   # Arbitrage detection and execution
├── logger.ts              # Structured logging
├── types.ts               # TypeScript type definitions
└── index.ts               # Main entry point
```

## Prerequisites

1. **Betfair Account**: You need a funded Betfair account
2. **Application Key**: Register for API access at [Betfair Developer Program](https://developer.betfair.com/)
3. **Node.js**: Version 18 or higher
4. **SSL Certificate** (recommended): For non-interactive bot login

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd betting-system
```

2. Install dependencies:
```bash
npm install
```

3. Configure your credentials:
```bash
cp .env.example .env
```

4. Edit `.env` and add your Betfair credentials:
```env
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
BETFAIR_APP_KEY=your_app_key
```

## Configuration

### Authentication Methods

#### Username/Password (Simple)
Set in `.env`:
```env
BETFAIR_USE_CERT=false
BETFAIR_USERNAME=your_username
BETFAIR_PASSWORD=your_password
BETFAIR_APP_KEY=your_app_key
```

#### SSL Certificate (Recommended for Bots)
1. Generate and download your SSL certificate from Betfair
2. Set in `.env`:
```env
BETFAIR_USE_CERT=true
BETFAIR_CERT_PATH=/path/to/certificate.crt
BETFAIR_KEY_PATH=/path/to/private.key
```

### Trading Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MIN_PROFIT_PERCENTAGE` | Minimum profit % to execute | 1.0 |
| `MAX_STAKE_PER_TRADE` | Maximum stake per trade | 50 |
| `AUTO_EXECUTE` | Enable automatic trade execution | false |
| `MAX_CONCURRENT_TRADES` | Max simultaneous trades | 3 |
| `BETFAIR_COMMISSION` | Betfair commission rate | 0.05 |

### Market Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `POLL_INTERVAL` | Market polling interval (ms) | 1000 |
| `MAX_MARKETS` | Maximum markets to monitor | 20 |
| `TARGET_SPORTS` | Sports to monitor (1=Soccer, 2=Tennis, 7=Horse Racing) | 1,2,7 |

## Usage

### Build the project
```bash
npm run build
```

### Run in production mode
```bash
npm start
```

### Run in development mode
```bash
npm run dev
```

### Running with Auto-Execute

**WARNING**: Auto-execute will place real bets with real money!

```bash
# In .env, set:
AUTO_EXECUTE=true
```

Then start the bot. It will automatically execute arbitrage opportunities that meet your criteria.

### Manual Mode (Recommended for Testing)

```bash
# In .env, set:
AUTO_EXECUTE=false
```

The bot will detect and log opportunities but won't place any bets automatically.

## How It Works

### 1. Authentication
- Logs into Betfair using username/password or SSL certificate
- Maintains session with automatic keep-alive

### 2. Market Discovery
- Queries Betfair for in-play markets in configured sports
- Focuses on high-liquidity markets (Match Odds, Over/Under)

### 3. Price Monitoring
- Polls selected markets at configured interval (default 1 second)
- Retrieves best available back and lay prices

### 4. Arbitrage Detection
- Calculates implied probabilities from back and lay odds
- Identifies opportunities where total implied probability < 100%
- Filters by minimum profit threshold

### 5. Trade Execution
- Calculates optimal stake sizes
- Places back bet first
- Immediately places matching lay bet
- Logs all activity and maintains trade history

### 6. Risk Management
- Validates all stakes and odds before placement
- Detects partial execution (one side fills, other fails)
- Limits concurrent trades
- Enforces maximum stake limits

## Example Output

```
[2025-11-15T10:30:45.123Z] [INFO] [Main] Starting Betfair Arbitrage Trading Bot...
[2025-11-15T10:30:45.456Z] [INFO] [Main] ✅ Authentication successful
[2025-11-15T10:30:45.789Z] [INFO] [Main] Account balance: £1000.00
[2025-11-15T10:30:46.012Z] [INFO] [Main] Found 15 markets to monitor
[2025-11-15T10:30:46.234Z] [INFO] [Main] 🚀 Bot is running and monitoring for arbitrage opportunities...

🎯 Arbitrage Opportunity Detected!
Market: 1.234567890
Selection: 12345
Back Price: 2.5 (Size: 100)
Lay Price: 2.48 (Size: 150)
Profit: 1.23%

💰 Executing arbitrage trade with stake: £25
Placing BACK bet at 2.5...
✅ Back bet placed: 987654321
Placing LAY bet at 2.48...
✅ Lay bet placed: 987654322

✨ Arbitrage executed successfully!
```

## API Rate Limits

- **listMarketBook**: Maximum 5 requests per second per market
- **placeOrders**: No specific limit but excessive requests may be throttled
- **Session Token**: Valid for 8 hours, automatically refreshed

## Betfair Commission

Betfair charges commission on net winnings:
- Standard: 5%
- Premium: 2-5% (varies by bet volume)
- Premium Plus: 2%

The bot accounts for commission in profit calculations.

## Testing

Before running with real money:

1. **Test with minimal stakes**:
```env
MAX_STAKE_PER_TRADE=2
DEFAULT_STAKE=2
```

2. **Set high profit threshold**:
```env
MIN_PROFIT_PERCENTAGE=5.0
```

3. **Enable auto-execute only after verifying**:
```env
AUTO_EXECUTE=false  # Start with false
```

4. **Monitor logs carefully** for any errors or unexpected behavior

## Troubleshooting

### Authentication Failed
- Verify username and password
- Check your app key is correct
- Ensure your account has API access enabled

### No Opportunities Detected
- True arbitrage on single selection is rare on Betfair
- Try lowering `MIN_PROFIT_PERCENTAGE`
- Consider monitoring more markets
- Look for cross-market arbitrage opportunities

### Partial Trade Execution
- If back bet succeeds but lay fails, you have unhedged exposure
- Monitor the "Partial" trades in logs
- Manually hedge the position in Betfair interface

### Rate Limit Errors
- Increase `POLL_INTERVAL` to reduce request frequency
- Decrease `MAX_MARKETS` to monitor fewer markets

## Security Best Practices

1. **Never commit `.env` file** - contains sensitive credentials
2. **Use SSL certificates** for production bots
3. **Enable 2FA** on your Betfair account
4. **Monitor account activity** regularly
5. **Use dedicated API keys** - don't reuse across projects
6. **Keep software updated** - npm packages may have security patches

## Limitations

- **Same-selection arbitrage is rare**: True arbitrage on a single selection is uncommon on Betfair
- **Market efficiency**: Betfair markets are highly efficient, reducing opportunities
- **Execution speed**: Price movements may occur between detection and execution
- **Commission impact**: 5% commission significantly reduces profitable opportunities
- **Liquidity risk**: Available liquidity may be insufficient for desired stakes

## Recommended Enhancements

For production use, consider adding:

1. **Streaming API**: Replace polling with WebSocket streaming for real-time data
2. **Multi-exchange support**: Monitor multiple bookmakers for cross-exchange arbitrage
3. **Database**: Store trade history in a database (PostgreSQL, MongoDB)
4. **Web UI**: Build a dashboard to monitor activity
5. **Alerts**: Send notifications via email/SMS for opportunities
6. **Advanced sizing**: Implement Kelly Criterion or other optimal sizing strategies
7. **Backtesting**: Test strategies on historical data
8. **ML integration**: Use machine learning to identify patterns

## API Documentation

- [Betfair Exchange API](https://docs.developer.betfair.com/)
- [Authentication Guide](https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Getting+Started)
- [Betting API Reference](https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Betting+API)
- [Stream API](https://docs.developer.betfair.com/display/1smk3cen4v3lu3yomq5qye0ni/Exchange+Stream+API)

## Support

For issues:
1. Check Betfair API documentation
2. Review logs for error messages
3. Test authentication separately
4. Verify account has sufficient funds

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

**Remember**: This is a sophisticated trading system dealing with real money. Always test thoroughly, understand the risks, and never bet more than you can afford to lose.
