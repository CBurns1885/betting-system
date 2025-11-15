/**
 * Betfair API Types and Interfaces
 */

export interface BetfairConfig {
  username: string;
  password: string;
  appKey: string;
  certPath?: string;
  keyPath?: string;
  useCert?: boolean;
}

export interface SessionToken {
  token: string;
  expiresAt: Date;
}

export interface MarketFilter {
  eventTypeIds?: string[];
  marketTypeCodes?: string[];
  marketIds?: string[];
  inPlayOnly?: boolean;
}

export interface PriceSize {
  price: number;
  size: number;
}

export interface RunnerBook {
  selectionId: number;
  handicap: number;
  status: string;
  adjustmentFactor?: number;
  lastPriceTraded?: number;
  totalMatched?: number;
  ex?: {
    availableToBack?: PriceSize[];
    availableToLay?: PriceSize[];
    tradedVolume?: PriceSize[];
  };
}

export interface MarketBook {
  marketId: string;
  isMarketDataDelayed: boolean;
  status: string;
  betDelay: number;
  bspReconciled: boolean;
  complete: boolean;
  inplay: boolean;
  numberOfWinners: number;
  numberOfRunners: number;
  numberOfActiveRunners: number;
  lastMatchTime?: Date;
  totalMatched?: number;
  totalAvailable?: number;
  crossMatching: boolean;
  runnersVoidable: boolean;
  version: number;
  runners: RunnerBook[];
}

export interface PlaceInstruction {
  orderType: 'LIMIT' | 'LIMIT_ON_CLOSE' | 'MARKET_ON_CLOSE';
  selectionId: number;
  handicap?: number;
  side: 'BACK' | 'LAY';
  limitOrder?: {
    size: number;
    price: number;
    persistenceType: 'LAPSE' | 'PERSIST' | 'MARKET_ON_CLOSE';
    timeInForce?: 'FILL_OR_KILL';
    minFillSize?: number;
  };
}

export interface PlaceOrdersRequest {
  marketId: string;
  instructions: PlaceInstruction[];
  customerRef?: string;
  marketVersion?: {
    version: number;
  };
  async?: boolean;
}

export interface PlaceInstructionReport {
  status: 'SUCCESS' | 'FAILURE' | 'TIMEOUT';
  errorCode?: string;
  instruction: PlaceInstruction;
  betId?: string;
  placedDate?: Date;
  averagePriceMatched?: number;
  sizeMatched?: number;
  orderStatus?: string;
}

export interface PlaceExecutionReport {
  status: 'SUCCESS' | 'FAILURE' | 'PROCESSED_WITH_ERRORS';
  marketId: string;
  instructionReports: PlaceInstructionReport[];
  errorCode?: string;
}

export interface ArbitrageOpportunity {
  marketId: string;
  selectionId: number;
  backPrice: number;
  layPrice: number;
  backSize: number;
  laySize: number;
  profit: number;
  profitPercentage: number;
  timestamp: Date;
}

export interface TradeExecution {
  opportunity: ArbitrageOpportunity;
  backBetId?: string;
  layBetId?: string;
  status: 'PENDING' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'PARTIAL';
  error?: string;
  executedAt?: Date;
}
