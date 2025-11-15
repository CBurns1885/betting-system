/**
 * Betfair API Client
 * Handles all API requests using JSON-RPC
 */

import axios, { AxiosInstance } from 'axios';
import { BetfairAuth } from './auth';
import {
  MarketBook,
  MarketFilter,
  PlaceOrdersRequest,
  PlaceExecutionReport,
} from './types';

export class BetfairClient {
  private auth: BetfairAuth;
  private readonly API_URL = 'https://api.betfair.com/exchange/betting/json-rpc/v1';
  private readonly NAVIGATION_URL = 'https://api.betfair.com/exchange/betting/rest/v1/en/navigation/menu.json';
  private requestId = 1;

  constructor(auth: BetfairAuth) {
    this.auth = auth;
  }

  /**
   * Make JSON-RPC request to Betfair API
   */
  private async makeRequest<T>(method: string, params: any): Promise<T> {
    const token = await this.auth.getToken();

    const payload = {
      jsonrpc: '2.0',
      method,
      params,
      id: this.requestId++,
    };

    try {
      const response = await axios.post(this.API_URL, payload, {
        headers: {
          'X-Application': await this.getAppKey(),
          'X-Authentication': token,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      });

      if (response.data.error) {
        throw new Error(
          `API Error: ${response.data.error.message} (${response.data.error.code})`
        );
      }

      return response.data.result;
    } catch (error: any) {
      if (error.response) {
        throw new Error(
          `API request failed: ${error.response.status} - ${error.response.statusText}`
        );
      }
      throw error;
    }
  }

  private async getAppKey(): Promise<string> {
    // Access the app key from auth config
    return (this.auth as any).config.appKey;
  }

  /**
   * List all market catalogues matching the filter
   */
  async listMarketCatalogue(
    filter: MarketFilter,
    maxResults: number = 100,
    marketProjection?: string[]
  ): Promise<any[]> {
    return this.makeRequest('SportsAPING/v1.0/listMarketCatalogue', {
      filter,
      maxResults,
      marketProjection: marketProjection || [
        'COMPETITION',
        'EVENT',
        'EVENT_TYPE',
        'MARKET_START_TIME',
        'MARKET_DESCRIPTION',
        'RUNNER_DESCRIPTION',
        'RUNNER_METADATA',
      ],
    });
  }

  /**
   * Get market books (prices and status) for specified markets
   */
  async listMarketBook(
    marketIds: string[],
    priceProjection?: {
      priceData?: ('EX_BEST_OFFERS' | 'EX_ALL_OFFERS' | 'EX_TRADED')[];
      virtualise?: boolean;
      rolloverStakes?: boolean;
    }
  ): Promise<MarketBook[]> {
    return this.makeRequest('SportsAPING/v1.0/listMarketBook', {
      marketIds,
      priceProjection: priceProjection || {
        priceData: ['EX_BEST_OFFERS', 'EX_TRADED'],
        virtualise: false,
      },
    });
  }

  /**
   * Place orders on a market
   */
  async placeOrders(request: PlaceOrdersRequest): Promise<PlaceExecutionReport> {
    return this.makeRequest('SportsAPING/v1.0/placeOrders', request);
  }

  /**
   * Cancel orders
   */
  async cancelOrders(
    marketId: string,
    betIds?: string[],
    sizeReduction?: number
  ): Promise<any> {
    const instructions = betIds?.map((betId) => ({
      betId,
      sizeReduction,
    })) || [];

    return this.makeRequest('SportsAPING/v1.0/cancelOrders', {
      marketId,
      instructions,
    });
  }

  /**
   * Replace orders (cancel and place new)
   */
  async replaceOrders(marketId: string, instructions: any[]): Promise<any> {
    return this.makeRequest('SportsAPING/v1.0/replaceOrders', {
      marketId,
      instructions,
    });
  }

  /**
   * List current orders
   */
  async listCurrentOrders(
    betIds?: string[],
    marketIds?: string[],
    orderProjection?: 'ALL' | 'EXECUTABLE' | 'EXECUTION_COMPLETE'
  ): Promise<any> {
    return this.makeRequest('SportsAPING/v1.0/listCurrentOrders', {
      betIds,
      marketIds,
      orderProjection: orderProjection || 'ALL',
    });
  }

  /**
   * List cleared orders (settled bets)
   */
  async listClearedOrders(
    betStatus?: 'SETTLED' | 'VOIDED' | 'LAPSED' | 'CANCELLED',
    eventTypeIds?: string[],
    marketIds?: string[],
    fromDate?: Date,
    toDate?: Date
  ): Promise<any> {
    return this.makeRequest('SportsAPING/v1.0/listClearedOrders', {
      betStatus: betStatus || 'SETTLED',
      eventTypeIds,
      marketIds,
      settledDateRange: fromDate && toDate ? {
        from: fromDate.toISOString(),
        to: toDate.toISOString(),
      } : undefined,
    });
  }

  /**
   * Get account funds
   */
  async getAccountFunds(): Promise<{
    availableToBetBalance: number;
    exposure: number;
    retainedCommission: number;
    exposureLimit: number;
    discountRate: number;
    pointsBalance: number;
  }> {
    return this.makeRequest('AccountAPING/v1.0/getAccountFunds', {});
  }

  /**
   * List event types (sports)
   */
  async listEventTypes(filter?: MarketFilter): Promise<any[]> {
    return this.makeRequest('SportsAPING/v1.0/listEventTypes', {
      filter: filter || {},
    });
  }

  /**
   * List competitions
   */
  async listCompetitions(filter: MarketFilter): Promise<any[]> {
    return this.makeRequest('SportsAPING/v1.0/listCompetitions', {
      filter,
    });
  }

  /**
   * List events
   */
  async listEvents(filter: MarketFilter): Promise<any[]> {
    return this.makeRequest('SportsAPING/v1.0/listEvents', {
      filter,
    });
  }
}
