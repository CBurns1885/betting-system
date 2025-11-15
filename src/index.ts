/**
 * Betfair Arbitrage Trading Bot
 * Main entry point
 */

import 'dotenv/config';
import { BetfairAuth } from './auth';
import { BetfairClient } from './betfair-client';
import { MarketMonitor } from './market-monitor';
import { OrderManager } from './order-manager';
import { ArbitrageExecutor } from './arbitrage-executor';
import { Logger, LogLevel } from './logger';

const logger = new Logger('Main', LogLevel.INFO);

async function main() {
  logger.info('Starting Betfair Arbitrage Trading Bot...');

  // Load configuration from environment variables
  const config = {
    username: process.env.BETFAIR_USERNAME || '',
    password: process.env.BETFAIR_PASSWORD || '',
    appKey: process.env.BETFAIR_APP_KEY || '',
    certPath: process.env.BETFAIR_CERT_PATH,
    keyPath: process.env.BETFAIR_KEY_PATH,
    useCert: process.env.BETFAIR_USE_CERT === 'true',
  };

  // Validate configuration
  if (!config.username || !config.password || !config.appKey) {
    logger.error('Missing required configuration. Please check your .env file');
    process.exit(1);
  }

  try {
    // Initialize authentication
    logger.info('Initializing Betfair authentication...');
    const auth = new BetfairAuth(config);
    await auth.login();
    logger.info('✅ Authentication successful');

    // Keep session alive every 4 hours
    setInterval(async () => {
      try {
        await auth.keepAlive();
        logger.info('Session refreshed');
      } catch (error: any) {
        logger.error('Failed to refresh session', error.message);
      }
    }, 4 * 60 * 60 * 1000);

    // Initialize API client
    const client = new BetfairClient(auth);

    // Get account balance
    const accountInfo = await client.getAccountFunds();
    logger.info(`Account balance: £${accountInfo.availableToBetBalance.toFixed(2)}`);
    logger.info(`Exposure: £${accountInfo.exposure.toFixed(2)}`);

    // Initialize order manager
    const orderManager = new OrderManager(client, {
      defaultStake: parseFloat(process.env.DEFAULT_STAKE || '10'),
      maxStake: parseFloat(process.env.MAX_STAKE || '100'),
      minOdds: parseFloat(process.env.MIN_ODDS || '1.01'),
      maxOdds: parseFloat(process.env.MAX_ODDS || '1000'),
      persistenceType: 'LAPSE',
    });

    // Initialize market monitor
    const pollInterval = parseInt(process.env.POLL_INTERVAL || '1000');
    const marketMonitor = new MarketMonitor(client, pollInterval);

    // Initialize arbitrage executor
    const arbitrageExecutor = new ArbitrageExecutor(orderManager, marketMonitor, {
      minProfitPercentage: parseFloat(process.env.MIN_PROFIT_PERCENTAGE || '1.0'),
      maxStakePerTrade: parseFloat(process.env.MAX_STAKE_PER_TRADE || '50'),
      enabled: process.env.ARBITRAGE_ENABLED !== 'false',
      autoExecute: process.env.AUTO_EXECUTE === 'true',
      maxConcurrentTrades: parseInt(process.env.MAX_CONCURRENT_TRADES || '3'),
      commission: parseFloat(process.env.BETFAIR_COMMISSION || '0.05'),
    });

    // Set up event listeners
    arbitrageExecutor.on('opportunityDetected', (opportunity) => {
      logger.info('Arbitrage opportunity detected', {
        marketId: opportunity.marketId,
        selectionId: opportunity.selectionId,
        profit: `${opportunity.profitPercentage.toFixed(2)}%`,
      });
    });

    arbitrageExecutor.on('executionStarted', (execution) => {
      logger.info('Executing arbitrage trade...');
    });

    arbitrageExecutor.on('executionCompleted', (execution) => {
      logger.info('✅ Trade executed successfully', {
        backBetId: execution.backBetId,
        layBetId: execution.layBetId,
      });
    });

    arbitrageExecutor.on('executionFailed', (execution) => {
      logger.error('❌ Trade execution failed', {
        error: execution.error,
        status: execution.status,
      });
    });

    marketMonitor.on('error', (error) => {
      logger.error('Market monitor error', error.message);
    });

    // Discover markets to monitor
    logger.info('Discovering markets...');
    const marketIds = await discoverMarkets(client);

    if (marketIds.length === 0) {
      logger.warn('No markets found to monitor');
      process.exit(0);
    }

    logger.info(`Found ${marketIds.length} markets to monitor`);
    marketMonitor.addMarkets(marketIds);

    // Start the arbitrage executor
    await arbitrageExecutor.start();

    logger.info('🚀 Bot is running and monitoring for arbitrage opportunities...');
    logger.info(`Auto-execute: ${arbitrageExecutor['config'].autoExecute ? 'ON' : 'OFF'}`);
    logger.info(`Min profit threshold: ${arbitrageExecutor['config'].minProfitPercentage}%`);

    // Graceful shutdown
    process.on('SIGINT', async () => {
      logger.info('\nShutting down gracefully...');
      arbitrageExecutor.stop();
      await auth.logout();
      logger.info('Goodbye!');
      process.exit(0);
    });

    // Log stats every 5 minutes
    setInterval(() => {
      const stats = arbitrageExecutor.getStats();
      logger.info('Trading Statistics', stats);
    }, 5 * 60 * 1000);
  } catch (error: any) {
    logger.error('Fatal error', error.message);
    process.exit(1);
  }
}

/**
 * Discover markets to monitor
 * You can customize this to focus on specific sports/events
 */
async function discoverMarkets(client: BetfairClient): Promise<string[]> {
  try {
    // Get event types (sports)
    const eventTypes = await client.listEventTypes();

    // Focus on popular sports with high liquidity
    // 1 = Soccer, 2 = Tennis, 4 = Cricket, 7 = Horse Racing
    const targetSports = process.env.TARGET_SPORTS?.split(',') || ['1', '2', '7'];

    // Get markets for in-play events
    const markets = await client.listMarketCatalogue(
      {
        eventTypeIds: targetSports,
        inPlayOnly: true, // Only in-play markets for faster price movements
        marketTypeCodes: ['MATCH_ODDS', 'OVER_UNDER_25'], // Main markets
      },
      parseInt(process.env.MAX_MARKETS || '20')
    );

    return markets.map((m) => m.marketId);
  } catch (error: any) {
    logger.error('Failed to discover markets', error.message);
    return [];
  }
}

// Run the bot
main().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
