/**
 * WebSocket Client Service
 * Handles real-time data subscriptions and updates
 */

import { WS_BASE_URL, WS_TOPICS, WS_CONFIG } from '@/config/api';

interface WebSocketMessage {
  type: string;
  topic?: string;
  data?: any;
  connection_id?: string;
  timestamp?: string;
}

interface WebSocketConnectionHandler {
  onConnectionChange?: (connected: boolean) => void;
}

type MessageHandler = (data: any) => void;
type ErrorHandler = (error: Event) => void;
type ConnectionHandler = () => void;

interface Subscription {
  topic: string;
  handler: (data: any) => void;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private subscriptions: Map<string, ((data: any) => void)[]> = new Map();
  private connectionId: string | null = null;
  private connectionHandlers: WebSocketConnectionHandler[] = [];
  private isConnecting = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectInterval = 2000;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isClient = false;
  private currentHost: string | null = null;
  private connectionCheckInterval: NodeJS.Timeout | null = null;

  // Event handlers
  private onConnectHandlers: ConnectionHandler[] = [];
  private onDisconnectHandlers: ConnectionHandler[] = [];
  private onErrorHandlers: ErrorHandler[] = [];

  constructor() {
    // Only initialize WebSocket in client environment
    if (typeof window !== 'undefined') {
      this.isClient = true;
      this.currentHost = this.getCurrentHost();
      console.log('Initializing WebSocket client with dynamic host:', this.currentHost);
      
      // Start connection check interval to detect IP changes
      this.startConnectionCheck();
      
      // Delay connection to avoid issues during static generation
      setTimeout(() => {
        this.connectWithCurrentHost();
      }, 100);
    }
  }

  /**
   * Get current host for WebSocket connection
   */
  private getCurrentHost(): string {
    if (typeof window === 'undefined') return 'localhost';
    
    // Check if using flexible configuration
    const useFlexible = process.env.NEXT_PUBLIC_USE_FLEXIBLE_CONFIG === 'true';
    if (useFlexible) {
      return window.location.hostname;
    }
    
    // Extract host from WS_BASE_URL
    try {
      const url = new URL(WS_BASE_URL.replace('ws://', 'http://'));
      return url.hostname;
    } catch {
      return window.location.hostname;
    }
  }

  /**
   * Start connection check to detect IP changes
   */
  private startConnectionCheck(): void {
    if (!this.isClient) return;
    
    this.connectionCheckInterval = setInterval(() => {
      const newHost = this.getCurrentHost();
      if (newHost !== this.currentHost) {
        console.log(`Host changed from ${this.currentHost} to ${newHost}, reconnecting...`);
        this.currentHost = newHost;
        this.forceReconnect();
      }
    }, 5000); // Check every 5 seconds
  }

  /**
   * Connect with current host
   */
  private connectWithCurrentHost(): void {
    const wsPort = process.env.NEXT_PUBLIC_WS_PORT || '8001';
    const fullUrl = `ws://${this.currentHost}:${wsPort}/ws/connect`;
    console.log('Attempting WebSocket connection to:', fullUrl);
    this.connect(fullUrl).catch(error => {
      console.error('WebSocket connection failed:', error);
    });
  }

  /**
   * Connect to WebSocket server
   */
  private connect(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // Only connect in client environment
      if (!this.isClient || typeof WebSocket === 'undefined') {
        reject(new Error('WebSocket not available'));
        return;
      }

      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      if (this.isConnecting) {
        resolve();
        return;
      }

      this.isConnecting = true;

      try {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
          console.log('WebSocket connected successfully to:', url);
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.connectionId = 'connected';
          this.notifyConnectionHandlers(true);
          this.resubscribeToTopics();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('WebSocket message parsing error:', error, 'Raw data:', event.data);
          }
        };

        this.ws.onclose = () => {
          this.isConnecting = false;
          this.stopHeartbeat();
          this.handleDisconnection();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket connection error to', url, ':', error);
          console.error('WebSocket readyState:', this.ws?.readyState);
          this.isConnecting = false;
          this.stopHeartbeat();
          reject(error);
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Handle WebSocket message event
   */
  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'connection_established':
        this.connectionId = message.connection_id || null;
        this.notifyConnectionHandlers(true);
        this.resubscribeToTopics();
        break;
      case 'subscription_response':
        break;
      case 'ping':
        this.sendPong();
        break;
      case 'pong':
        // Handle pong
        break;
      case 'unsubscription_response':
        // Legacy handler notification for backwards compatibility
        if (message.topic) {
          const legacyHandlers = this.subscriptions.get(message.topic) || [];
          legacyHandlers.forEach(handler => {
            try {
              handler(message);
            } catch (error) {
              // Silent error handling
            }
          });
        }
        break;
      case 'data_update':
      case 'experiments_overview_update':
      case 'device_data_update':
      case 'device_detail_update':
      case 'device_port_analysis_update':
      case 'device_protocol_distribution_update':
      case 'device_traffic_trend_update':
      case 'device_network_topology_update':
      case 'device_activity_timeline_update':
        if (message.topic) {
          this.notifySubscribers(message.topic, message.data);
        }
        break;
      default:
        break;
    }
  }

  private notifySubscribers(topic: string, data: any) {
    const handlers = this.subscriptions.get(topic) || [];
    handlers.forEach(handler => {
      try {
        handler(data);
      } catch (error) {
        // Silent error handling
      }
    });
  }

  private notifyConnectionHandlers(connected: boolean) {
    this.connectionHandlers.forEach(handler => {
      try {
        handler.onConnectionChange?.(connected);
      } catch (error) {
        // Silent error handling
      }
    });
  }

  private handleDisconnection() {
    this.connectionId = null;
    this.notifyConnectionHandlers(false);
    
    // 增加重连尝试次数，提高可靠性
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      
      // 使用指数退避策略
      const delay = Math.min(this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1), 30000);
      setTimeout(() => {
        this.reconnect();
      }, delay);
    } else {
      // 重置重连计数器，允许后续重新尝试
      setTimeout(() => {
        this.reconnectAttempts = 0;
      }, 60000); // 1分钟后重置
    }
  }

  private async reconnect() {
    if (!this.isClient || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      // Always use current host for reconnection
      this.currentHost = this.getCurrentHost();
      this.connectWithCurrentHost();
    } catch (error) {
      // Silent error handling
    }
  }

  private resubscribeToTopics() {
    const activeTopics = Array.from(this.subscriptions.keys());
    console.log('Resubscribing to topics:', activeTopics);
    
    activeTopics.forEach(topic => {
      const handlers = this.subscriptions.get(topic);
      if (handlers && handlers.length > 0) {
        console.log('Resubscribing to topic:', topic, 'with', handlers.length, 'handlers');
        this.sendSubscription(topic);
      }
    });
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    if (!this.isClient) return;
    
    this.heartbeatInterval = setInterval(() => {
      this.sendPing();
    }, WS_CONFIG.heartbeatInterval);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private sendPing() {
    this.sendMessage({
      type: 'ping',
      timestamp: new Date().toISOString()
    });
  }

  private sendPong() {
    this.sendMessage({
      type: 'pong',
      timestamp: new Date().toISOString()
    });
  }

  private sendMessage(message: any) {
    if (this.isClient && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Send subscription message to server
   */
  private sendSubscription(topic: string): void {
    this.sendMessage({
      type: 'subscribe',
      topic: topic
    });
  }

  /**
   * Subscribe to a topic
   */
  subscribe(topic: string, handler: (data: any) => void): () => void {
    
    if (!this.subscriptions.has(topic)) {
      this.subscriptions.set(topic, []);
    }
    
    const handlers = this.subscriptions.get(topic)!;
    const isFirstSubscription = handlers.length === 0;
    
    // Always try to send subscription when adding first handler
    if (isFirstSubscription) {
      if (this.isClient && this.ws?.readyState === WebSocket.OPEN) {
        console.log('Subscribing to topic:', topic);
        this.sendSubscription(topic);
      } else {
        console.log('WebSocket not ready, queuing subscription for topic:', topic, 'readyState:', this.ws?.readyState);
      }
    }
    
    handlers.push(handler);

    return () => {
      this.unsubscribe(topic, handler);
    };
  }

  /**
   * Unsubscribe from a topic
   */
  unsubscribe(topic: string, handler: (data: any) => void): void {
    const handlers = this.subscriptions.get(topic);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
        
        if (handlers.length === 0) {
          this.subscriptions.delete(topic);
          if (this.isClient) {
            this.sendMessage({
              type: 'unsubscribe',
              topic: topic
            });
          }
        }
      }
    }
  }

  /**
   * Add connection event handler
   */
  addConnectionHandler(handler: WebSocketConnectionHandler): () => void {
    this.connectionHandlers.push(handler);
    
    if (this.isClient && this.ws?.readyState === WebSocket.OPEN) {
      handler.onConnectionChange?.(true);
    }
    
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.isClient && this.ws?.readyState === WebSocket.OPEN;
  }

  getConnectionId(): string | null {
    return this.connectionId;
  }

  /**
   * Force reconnect WebSocket connection
   */
  forceReconnect(): void {
    if (!this.isClient) return;
    
    this.reconnectAttempts = 0; // 重置重连计数器
    
    // 先关闭现有连接
    if (this.ws) {
      this.ws.close();
    }
    
    // 延迟重连以确保连接完全关闭
    setTimeout(() => {
      this.reconnect();
    }, 1000);
  }

  /**
   * Close WebSocket connection
   */
  disconnect(): void {
    this.stopHeartbeat();
    
    if (this.connectionCheckInterval) {
      clearInterval(this.connectionCheckInterval);
      this.connectionCheckInterval = null;
    }
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    this.connectionId = null;
    this.subscriptions.clear();
    this.connectionHandlers = [];
  }
}

// Export singleton instance
const websocketService = new WebSocketService();
export default websocketService; 