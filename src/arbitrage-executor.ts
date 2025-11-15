/**
 * Arbitrage Executor
 * Executes arbitrage opportunities automatically
 */

import { EventEmitter } from 'events';
import { OrderManager } from './order-manager';
import { MarketMonitor } from './market-monitor';
import { ArbitrageOpportunity, TradeExecution } from './types';

export interface ArbitrageConfig {
  minProfitPercentage: number;
  maxStakePerTrade: number;
  enabled: boolean;
  autoExecute: boolean;
  maxConcurrentTrades: number;
  commission: number; // Betfair commission rate (e.g., 0.05 for 5%)
}

export class ArbitrageExecutor extends EventEmitter {
  private orderManager: OrderManager;
  private marketMonitor: MarketMonitor;
  private config: ArbitrageConfig;
  private activeTrades: Map<string, TradeExecution> = new Map();
  private tradeHistory: TradeExecution[] = [];

  constructor(
    orderManager: OrderManager,
    marketMonitor: MarketMonitor,
    config: ArbitrageConfig
  ) {
    super();
    this.orderManager = orderManager;
    this.marketMonitor = marketMonitor;
    this.config = config;

    // Listen for arbitrage opportunities from market monitor
    this.marketMonitor.on('arbitrageOpportunity', (opportunity: ArbitrageOpportunity) => {
      this.handleOpportunity(opportunity);
    });
  }

  /**
   * Start the arbitrage executor
   */
  async start(): Promise<void> {
    if (!this.config.enabled) {
      console.log('Arbitrage executor is disabled');
      return;
    }

    console.log('Starting arbitrage executor...');
    await this.marketMonitor.start();
  }

  /**
   * Stop the arbitrage executor
   */
  stop(): void {
    console.log('Stopping arbitrage executor...');
    this.marketMonitor.stop();
  }

  /**
   * Handle an arbitrage opportunity
   */
  private async handleOpportunity(opportunity: ArbitrageOpportunity): Promise<void> {
    // Check if we should execute this opportunity
    if (!this.shouldExecute(opportunity)) {
      return;
    }

    console.log('\n🎯 Arbitrage Opportunity Detected!');
    console.log(`Market: ${opportunity.marketId}`);
    console.log(`Selection: ${opportunity.selectionId}`);
    console.log(`Back Price: ${opportunity.backPrice} (Size: ${opportunity.backSize})`);
    console.log(`Lay Price: ${opportunity.layPrice} (Size: ${opportunity.laySize})`);
    console.log(`Profit: ${(opportunity.profitPercentage).toFixed(2)}%`);

    this.emit('opportunityDetected', opportunity);

    if (this.config.autoExecute) {
      await this.executeArbitrage(opportunity);
    }
  }

  /**
   * Check if opportunity should be executed
   */
  private shouldExecute(opportunity: ArbitrageOpportunity): boolean {
    // Check minimum profit threshold
    if (opportunity.profitPercentage < this.config.minProfitPercentage) {
      return false;
    }

    // Check if we're at max concurrent trades
    if (this.activeTrades.size >= this.config.maxConcurrentTrades) {
      console.log('Max concurrent trades reached, skipping opportunity');
      return false;
    }

    // Check if we already have a trade on this market/selection
    const tradeKey = `${opportunity.marketId}-${opportunity.selectionId}`;
    if (this.activeTrades.has(tradeKey)) {
      return false;
    }

    return true;
  }

  /**
   * Execute an arbitrage opportunity
   */
  async executeArbitrage(opportunity: ArbitrageOpportunity): Promise<TradeExecution> {
    const tradeKey = `${opportunity.marketId}-${opportunity.selectionId}`;

    const execution: TradeExecution = {
      opportunity,
      status: 'PENDING',
    };

    this.activeTrades.set(tradeKey, execution);

    try {
      execution.status = 'EXECUTING';
      this.emit('executionStarted', execution);

      // Calculate optimal stake considering commission
      const stake = this.calculateOptimalStake(opportunity);

      console.log(`\n💰 Executing arbitrage trade with stake: £${stake}`);

      // Place back bet
      console.log(`Placing BACK bet at ${opportunity.backPrice}...`);
      const backResult = await this.orderManager.placeBackBet(
        opportunity.marketId,
        opportunity.selectionId,
        opportunity.backPrice,
        stake
      );

      if (backResult.status !== 'SUCCESS') {
        throw new Error(`Back bet failed: ${backResult.errorCode}`);
      }

      execution.backBetId = backResult.betId;
      console.log(`✅ Back bet placed: ${backResult.betId}`);

      // Calculate lay stake to balance the book
      const layStake = this.calculateLayStake(stake, opportunity.backPrice, opportunity.layPrice);

      // Place lay bet
      console.log(`Placing LAY bet at ${opportunity.layPrice}...`);
      const layResult = await this.orderManager.placeLayBet(
        opportunity.marketId,
        opportunity.selectionId,
        opportunity.layPrice,
        layStake
      );

      if (layResult.status !== 'SUCCESS') {
        // Back bet succeeded but lay failed - we have exposure!
        execution.status = 'PARTIAL';
        execution.error = `Lay bet failed: ${layResult.errorCode}`;
        console.error(`⚠️  WARNING: Lay bet failed but back bet succeeded!`);
        console.error(`You have unhedged exposure on bet ${execution.backBetId}`);

        this.emit('executionFailed', execution);
        return execution;
      }

      execution.layBetId = layResult.betId;
      execution.status = 'COMPLETED';
      execution.executedAt = new Date();

      console.log(`✅ Lay bet placed: ${layResult.betId}`);
      console.log(`\n✨ Arbitrage executed successfully!`);

      this.emit('executionCompleted', execution);
      this.tradeHistory.push(execution);

      // Remove from active trades after a delay
      setTimeout(() => {
        this.activeTrades.delete(tradeKey);
      }, 60000); // 1 minute

      return execution;
    } catch (error: any) {
      execution.status = 'FAILED';
      execution.error = error.message;

      console.error(`❌ Arbitrage execution failed: ${error.message}`);

      this.emit('executionFailed', execution);
      this.activeTrades.delete(tradeKey);

      return execution;
    }
  }

  /**
   * Calculate optimal stake for arbitrage
   */
  private calculateOptimalStake(opportunity: ArbitrageOpportunity): number {
    // Use the smaller of available sizes to ensure both bets can be matched
    const maxStake = Math.min(
      opportunity.backSize,
      opportunity.laySize,
      this.config.maxStakePerTrade
    );

    // Account for commission in profit calculation
    const netProfit = opportunity.profitPercentage * (1 - this.config.commission);

    // For now, use a conservative percentage of max available
    // In production, you'd want more sophisticated sizing algorithms
    return Math.min(maxStake * 0.5, this.config.maxStakePerTrade);
  }

  /**
   * Calculate lay stake to balance the book
   */
  private calculateLayStake(backStake: number, backOdds: number, layOdds: number): number {
    // To balance: backStake * backOdds = layStake * layOdds
    // layStake = (backStake * backOdds) / layOdds
    const layStake = (backStake * backOdds) / layOdds;
    return Math.round(layStake * 100) / 100;
  }

  /**
   * Get active trades
   */
  getActiveTrades(): TradeExecution[] {
    return Array.from(this.activeTrades.values());
  }

  /**
   * Get trade history
   */
  getTradeHistory(limit: number = 50): TradeExecution[] {
    return this.tradeHistory.slice(-limit);
  }

  /**
   * Get statistics
   */
  getStats(): {
    totalTrades: number;
    successfulTrades: number;
    failedTrades: number;
    partialTrades: number;
    activeTrades: number;
  } {
    const successful = this.tradeHistory.filter((t) => t.status === 'COMPLETED').length;
    const failed = this.tradeHistory.filter((t) => t.status === 'FAILED').length;
    const partial = this.tradeHistory.filter((t) => t.status === 'PARTIAL').length;

    return {
      totalTrades: this.tradeHistory.length,
      successfulTrades: successful,
      failedTrades: failed,
      partialTrades: partial,
      activeTrades: this.activeTrades.size,
    };
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<ArbitrageConfig>): void {
    this.config = { ...this.config, ...config };

    if (config.enabled === false) {
      this.stop();
    }
  }

  /**
   * Enable/disable auto execution
   */
  setAutoExecute(enabled: boolean): void {
    this.config.autoExecute = enabled;
    console.log(`Auto-execution ${enabled ? 'enabled' : 'disabled'}`);
  }
}
