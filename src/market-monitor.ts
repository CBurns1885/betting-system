/**
 * Market Monitor
 * Continuously monitors markets for price updates
 */

import { BetfairClient } from './betfair-client';
import { MarketBook, MarketFilter, ArbitrageOpportunity } from './types';
import { EventEmitter } from 'events';

export class MarketMonitor extends EventEmitter {
  private client: BetfairClient;
  private monitoredMarkets: Set<string> = new Set();
  private isRunning = false;
  private pollInterval = 1000; // 1 second (max 5 requests per second per market)
  private intervalId?: NodeJS.Timeout;

  constructor(client: BetfairClient, pollInterval: number = 1000) {
    super();
    this.client = client;
    this.pollInterval = Math.max(pollInterval, 200); // Min 200ms to stay under 5/sec limit
  }

  /**
   * Add markets to monitor
   */
  addMarkets(marketIds: string[]): void {
    marketIds.forEach((id) => this.monitoredMarkets.add(id));
  }

  /**
   * Remove markets from monitoring
   */
  removeMarkets(marketIds: string[]): void {
    marketIds.forEach((id) => this.monitoredMarkets.delete(id));
  }

  /**
   * Start monitoring markets
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      console.log('Market monitor already running');
      return;
    }

    this.isRunning = true;
    console.log(`Starting market monitor (interval: ${this.pollInterval}ms)`);

    this.intervalId = setInterval(async () => {
      await this.pollMarkets();
    }, this.pollInterval);

    // Initial poll
    await this.pollMarkets();
  }

  /**
   * Stop monitoring markets
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = undefined;
    }
    this.isRunning = false;
    console.log('Market monitor stopped');
  }

  /**
   * Poll all monitored markets for updates
   */
  private async pollMarkets(): Promise<void> {
    if (this.monitoredMarkets.size === 0) {
      return;
    }

    try {
      const marketIds = Array.from(this.monitoredMarkets);
      const marketBooks = await this.client.listMarketBook(marketIds, {
        priceData: ['EX_BEST_OFFERS'],
        virtualise: false,
      });

      // Emit update event for each market
      for (const marketBook of marketBooks) {
        this.emit('marketUpdate', marketBook);

        // Check for arbitrage opportunities
        const opportunities = this.detectArbitrage(marketBook);
        for (const opportunity of opportunities) {
          this.emit('arbitrageOpportunity', opportunity);
        }
      }
    } catch (error: any) {
      this.emit('error', error);
      console.error('Error polling markets:', error.message);
    }
  }

  /**
   * Detect arbitrage opportunities in a market
   * Arbitrage exists when back odds on one selection are higher than lay odds on another
   */
  private detectArbitrage(marketBook: MarketBook): ArbitrageOpportunity[] {
    const opportunities: ArbitrageOpportunity[] = [];

    // Skip if market is delayed or not in-play and we're looking for live arb
    if (marketBook.isMarketDataDelayed) {
      return opportunities;
    }

    for (const runner of marketBook.runners) {
      if (!runner.ex?.availableToBack || !runner.ex?.availableToLay) {
        continue;
      }

      const bestBack = runner.ex.availableToBack[0];
      const bestLay = runner.ex.availableToLay[0];

      if (!bestBack || !bestLay) {
        continue;
      }

      // Simple arbitrage: when we can back and lay at profitable odds
      // For a true arbitrage, we need lay price < back price
      // This is rare on same selection, more common across different bookmakers
      // Here we check if spread is very tight indicating potential opportunity

      const spread = bestLay.price - bestBack.price;
      const spreadPercentage = (spread / bestBack.price) * 100;

      // Also check for back/lay imbalance that might indicate value
      if (bestBack.price > 1.01 && bestLay.price < 1000) {
        const backImpliedProb = 1 / bestBack.price;
        const layImpliedProb = 1 / bestLay.price;
        const totalProb = backImpliedProb + layImpliedProb;

        // If total probability < 1, there's an arbitrage opportunity
        if (totalProb < 0.98) { // Allow small margin for commission
          const profit = 1 - totalProb;
          const profitPercentage = profit * 100;

          opportunities.push({
            marketId: marketBook.marketId,
            selectionId: runner.selectionId,
            backPrice: bestBack.price,
            layPrice: bestLay.price,
            backSize: bestBack.size,
            laySize: bestLay.size,
            profit,
            profitPercentage,
            timestamp: new Date(),
          });
        }
      }
    }

    return opportunities;
  }

  /**
   * Get current status
   */
  getStatus(): {
    running: boolean;
    monitoredMarkets: number;
    pollInterval: number;
  } {
    return {
      running: this.isRunning,
      monitoredMarkets: this.monitoredMarkets.size,
      pollInterval: this.pollInterval,
    };
  }
}
