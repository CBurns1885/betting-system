/**
 * Order Manager
 * Handles order placement and management
 */

import { BetfairClient } from './betfair-client';
import {
  PlaceInstruction,
  PlaceOrdersRequest,
  PlaceExecutionReport,
  PlaceInstructionReport,
} from './types';

export interface OrderConfig {
  defaultStake: number;
  maxStake: number;
  minOdds: number;
  maxOdds: number;
  persistenceType: 'LAPSE' | 'PERSIST' | 'MARKET_ON_CLOSE';
}

export class OrderManager {
  private client: BetfairClient;
  private config: OrderConfig;

  constructor(client: BetfairClient, config: OrderConfig) {
    this.client = client;
    this.config = config;
  }

  /**
   * Place a single back bet
   */
  async placeBackBet(
    marketId: string,
    selectionId: number,
    price: number,
    size: number,
    handicap: number = 0
  ): Promise<PlaceInstructionReport> {
    const instruction: PlaceInstruction = {
      orderType: 'LIMIT',
      selectionId,
      handicap,
      side: 'BACK',
      limitOrder: {
        size: this.validateStake(size),
        price: this.validateOdds(price),
        persistenceType: this.config.persistenceType,
      },
    };

    const request: PlaceOrdersRequest = {
      marketId,
      instructions: [instruction],
    };

    const result = await this.client.placeOrders(request);
    return result.instructionReports[0];
  }

  /**
   * Place a single lay bet
   */
  async placeLayBet(
    marketId: string,
    selectionId: number,
    price: number,
    size: number,
    handicap: number = 0
  ): Promise<PlaceInstructionReport> {
    const instruction: PlaceInstruction = {
      orderType: 'LIMIT',
      selectionId,
      handicap,
      side: 'LAY',
      limitOrder: {
        size: this.validateStake(size),
        price: this.validateOdds(price),
        persistenceType: this.config.persistenceType,
      },
    };

    const request: PlaceOrdersRequest = {
      marketId,
      instructions: [instruction],
    };

    const result = await this.client.placeOrders(request);
    return result.instructionReports[0];
  }

  /**
   * Place multiple orders atomically
   */
  async placeMultipleOrders(
    marketId: string,
    instructions: PlaceInstruction[]
  ): Promise<PlaceExecutionReport> {
    // Validate all instructions
    for (const instruction of instructions) {
      if (instruction.limitOrder) {
        instruction.limitOrder.size = this.validateStake(instruction.limitOrder.size);
        instruction.limitOrder.price = this.validateOdds(instruction.limitOrder.price);
      }
    }

    const request: PlaceOrdersRequest = {
      marketId,
      instructions,
    };

    return await this.client.placeOrders(request);
  }

  /**
   * Place hedging orders (back and lay on same selection)
   */
  async placeHedge(
    marketId: string,
    selectionId: number,
    backPrice: number,
    layPrice: number,
    stake: number
  ): Promise<PlaceExecutionReport> {
    const backInstruction: PlaceInstruction = {
      orderType: 'LIMIT',
      selectionId,
      side: 'BACK',
      limitOrder: {
        size: this.validateStake(stake),
        price: this.validateOdds(backPrice),
        persistenceType: this.config.persistenceType,
      },
    };

    const layInstruction: PlaceInstruction = {
      orderType: 'LIMIT',
      selectionId,
      side: 'LAY',
      limitOrder: {
        size: this.validateStake(stake),
        price: this.validateOdds(layPrice),
        persistenceType: this.config.persistenceType,
      },
    };

    return await this.placeMultipleOrders(marketId, [backInstruction, layInstruction]);
  }

  /**
   * Cancel orders
   */
  async cancelOrders(marketId: string, betIds: string[]): Promise<any> {
    return await this.client.cancelOrders(marketId, betIds);
  }

  /**
   * Get current open orders
   */
  async getCurrentOrders(marketIds?: string[]): Promise<any> {
    return await this.client.listCurrentOrders(undefined, marketIds, 'ALL');
  }

  /**
   * Validate stake amount
   */
  private validateStake(stake: number): number {
    if (stake < 2) {
      throw new Error('Minimum stake is £2');
    }
    if (stake > this.config.maxStake) {
      console.warn(`Stake ${stake} exceeds max ${this.config.maxStake}, using max`);
      return this.config.maxStake;
    }
    // Round to 2 decimal places
    return Math.round(stake * 100) / 100;
  }

  /**
   * Validate odds
   */
  private validateOdds(odds: number): number {
    if (odds < this.config.minOdds) {
      throw new Error(`Odds ${odds} below minimum ${this.config.minOdds}`);
    }
    if (odds > this.config.maxOdds) {
      throw new Error(`Odds ${odds} above maximum ${this.config.maxOdds}`);
    }

    // Round to valid Betfair price increment
    return this.roundToValidPrice(odds);
  }

  /**
   * Round to valid Betfair price increments
   */
  private roundToValidPrice(price: number): number {
    // Betfair has specific price increments
    // 1.01 - 2.00: 0.01 increments
    // 2.00 - 3.00: 0.02 increments
    // 3.00 - 4.00: 0.05 increments
    // 4.00 - 6.00: 0.1 increments
    // 6.00 - 10.00: 0.2 increments
    // 10.00 - 20.00: 0.5 increments
    // 20.00 - 30.00: 1 increments
    // 30.00 - 50.00: 2 increments
    // 50.00 - 100.00: 5 increments
    // 100.00 - 1000.00: 10 increments

    if (price < 2) return Math.round(price * 100) / 100;
    if (price < 3) return Math.round(price * 50) / 50;
    if (price < 4) return Math.round(price * 20) / 20;
    if (price < 6) return Math.round(price * 10) / 10;
    if (price < 10) return Math.round(price * 5) / 5;
    if (price < 20) return Math.round(price * 2) / 2;
    if (price < 30) return Math.round(price);
    if (price < 50) return Math.round(price / 2) * 2;
    if (price < 100) return Math.round(price / 5) * 5;
    return Math.round(price / 10) * 10;
  }

  /**
   * Calculate liability for a lay bet
   */
  calculateLayLiability(stake: number, odds: number): number {
    return stake * (odds - 1);
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<OrderConfig>): void {
    this.config = { ...this.config, ...config };
  }
}
