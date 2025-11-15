/**
 * Betfair Authentication Module
 * Handles login and session management
 */

import axios, { AxiosInstance } from 'axios';
import { readFileSync } from 'fs';
import https from 'https';
import { BetfairConfig, SessionToken } from './types';

export class BetfairAuth {
  private config: BetfairConfig;
  private sessionToken: SessionToken | null = null;
  private readonly LOGIN_URL = 'https://identitysso.betfair.com/api/login';
  private readonly CERT_LOGIN_URL = 'https://identitysso-cert.betfair.com/api/certlogin';
  private readonly KEEP_ALIVE_URL = 'https://identitysso.betfair.com/api/keepAlive';

  constructor(config: BetfairConfig) {
    this.config = config;
  }

  /**
   * Login to Betfair using username/password or SSL certificate
   */
  async login(): Promise<string> {
    try {
      if (this.config.useCert && this.config.certPath && this.config.keyPath) {
        return await this.loginWithCert();
      } else {
        return await this.loginWithPassword();
      }
    } catch (error: any) {
      throw new Error(`Authentication failed: ${error.message}`);
    }
  }

  /**
   * Login using username and password
   */
  private async loginWithPassword(): Promise<string> {
    const response = await axios.post(
      this.LOGIN_URL,
      new URLSearchParams({
        username: this.config.username,
        password: this.config.password,
      }),
      {
        headers: {
          'X-Application': this.config.appKey,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

    if (response.data.loginStatus !== 'SUCCESS') {
      throw new Error(`Login failed: ${response.data.loginStatus}`);
    }

    const token = response.data.sessionToken;
    this.sessionToken = {
      token,
      expiresAt: new Date(Date.now() + 8 * 60 * 60 * 1000), // 8 hours
    };

    return token;
  }

  /**
   * Login using SSL certificate (recommended for bots)
   */
  private async loginWithCert(): Promise<string> {
    if (!this.config.certPath || !this.config.keyPath) {
      throw new Error('Certificate paths not configured');
    }

    const cert = readFileSync(this.config.certPath);
    const key = readFileSync(this.config.keyPath);

    const httpsAgent = new https.Agent({
      cert,
      key,
      rejectUnauthorized: true,
    });

    const response = await axios.post(
      this.CERT_LOGIN_URL,
      new URLSearchParams({
        username: this.config.username,
        password: this.config.password,
      }),
      {
        headers: {
          'X-Application': this.config.appKey,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        httpsAgent,
      }
    );

    if (response.data.loginStatus !== 'SUCCESS') {
      throw new Error(`Certificate login failed: ${response.data.loginStatus}`);
    }

    const token = response.data.sessionToken;
    this.sessionToken = {
      token,
      expiresAt: new Date(Date.now() + 8 * 60 * 60 * 1000), // 8 hours
    };

    return token;
  }

  /**
   * Keep session alive by refreshing the token
   */
  async keepAlive(): Promise<void> {
    if (!this.sessionToken) {
      throw new Error('No active session to keep alive');
    }

    const response = await axios.post(
      this.KEEP_ALIVE_URL,
      {},
      {
        headers: {
          'X-Application': this.config.appKey,
          'X-Authentication': this.sessionToken.token,
        },
      }
    );

    if (response.data.status !== 'SUCCESS') {
      throw new Error('Failed to keep session alive');
    }

    // Extend token expiration
    this.sessionToken.expiresAt = new Date(Date.now() + 8 * 60 * 60 * 1000);
  }

  /**
   * Get current session token
   */
  async getToken(): Promise<string> {
    if (!this.sessionToken || this.isTokenExpired()) {
      return await this.login();
    }
    return this.sessionToken.token;
  }

  /**
   * Check if token is expired or about to expire
   */
  private isTokenExpired(): boolean {
    if (!this.sessionToken) return true;
    // Refresh if less than 30 minutes remaining
    return this.sessionToken.expiresAt.getTime() - Date.now() < 30 * 60 * 1000;
  }

  /**
   * Logout from Betfair
   */
  async logout(): Promise<void> {
    if (this.sessionToken) {
      await axios.post(
        'https://identitysso.betfair.com/api/logout',
        {},
        {
          headers: {
            'X-Application': this.config.appKey,
            'X-Authentication': this.sessionToken.token,
          },
        }
      );
      this.sessionToken = null;
    }
  }
}
