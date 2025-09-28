import { useState, useEffect, useRef, useCallback } from 'react';
import { WS_BASE_URL } from '../utils/constants';
import { useAuthToken } from '../store/authSlice';
import { useSchedulingStore } from '../store/schedulingSlice';

// Types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  id?: string;
}

export interface WebSocketOptions {
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface UseWebSocketReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'error';
  error: string | null;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (type: string, data: any) => void;
  
  // Message handling
  lastMessage: WebSocketMessage | null;
  messageHistory: WebSocketMessage[];
  
  // Connection stats
  reconnectAttempts: number;
  lastReconnectTime: Date | null;
}

export const useWebSocket = (
  endpoint: string = '/optimization',
  options: WebSocketOptions = {}
): UseWebSocketReturn => {
  const {
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 3000,
    heartbeatInterval = 30000,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  // Auth token for WebSocket authentication
  const token = useAuthToken();
  
  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionState, setConnectionState] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [messageHistory, setMessageHistory] = useState<WebSocketMessage[]>([]);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastReconnectTime, setLastReconnectTime] = useState<Date | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isManuallyDisconnected = useRef(false);

  // Build WebSocket URL with auth token
  const buildWebSocketUrl = useCallback(() => {
    const wsUrl = new URL(endpoint, WS_BASE_URL);
    if (token) {
      wsUrl.searchParams.set('token', token);
    }
    return wsUrl.toString();
  }, [endpoint, token]);

  // Clear timeouts
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Heartbeat mechanism
  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval > 0) {
      heartbeatTimeoutRef.current = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'ping',
            timestamp: new Date().toISOString(),
          }));
        }
      }, heartbeatInterval);
    }
  }, [heartbeatInterval]);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      setLastMessage(message);
      setMessageHistory(prev => [...prev.slice(-99), message]); // Keep last 100 messages

      // Handle different message types
      switch (message.type) {
        case 'optimization_progress':
          useSchedulingStore.getState().updateOptimizationProgress(message.data);
          break;
        
        case 'optimization_complete':
          useSchedulingStore.getState().setSchedule(message.data.schedule);
          useSchedulingStore.getState().setConflicts(message.data.conflicts);
          useSchedulingStore.getState().updateOptimizationProgress({
            phase: 'complete',
            progress: 1,
            eta: 0,
            message: 'Optimization completed successfully',
          });
          break;
        
        case 'conflict_update':
          useSchedulingStore.getState().setConflicts(message.data);
          break;
        
        case 'schedule_update':
          useSchedulingStore.getState().setSchedule(message.data);
          break;
        
        case 'error':
          setError(message.data.message || 'WebSocket error occurred');
          break;
        
        case 'pong':
          // Handle heartbeat response
          break;
        
        default:
          console.log('Unhandled WebSocket message type:', message.type);
      }

      // Call custom message handler
      onMessage?.(message);

    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      setError('Failed to parse incoming message');
    }
  }, [onMessage]);

  // Reconnect logic
  const attemptReconnect = useCallback(() => {
    if (!autoReconnect || isManuallyDisconnected.current || reconnectAttempts >= maxReconnectAttempts) {
      return;
    }

    const delay = reconnectDelay * Math.pow(1.5, reconnectAttempts); // Exponential backoff
    
    reconnectTimeoutRef.current = setTimeout(() => {
      setReconnectAttempts(prev => prev + 1);
      setLastReconnectTime(new Date());
      connect();
    }, delay);
  }, [autoReconnect, reconnectAttempts, maxReconnectAttempts, reconnectDelay]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token) {
      setError('Authentication token required');
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    isManuallyDisconnected.current = false;
    setIsConnecting(true);
    setConnectionState('connecting');
    setError(null);
    clearTimeouts();

    try {
      const ws = new WebSocket(buildWebSocketUrl());
      wsRef.current = ws;

      ws.onopen = (event) => {
        setIsConnected(true);
        setIsConnecting(false);
        setConnectionState('connected');
        setReconnectAttempts(0);
        setError(null);
        
        startHeartbeat();
        onOpen?.(event);
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        setIsConnected(false);
        setIsConnecting(false);
        stopHeartbeat();
        clearTimeouts();

        if (!isManuallyDisconnected.current) {
          setConnectionState('error');
          
          // Attempt reconnection if not manually disconnected
          if (autoReconnect && reconnectAttempts < maxReconnectAttempts) {
            attemptReconnect();
          }
        } else {
          setConnectionState('disconnected');
        }

        onClose?.(event);
      };

      ws.onerror = (event) => {
        setError('WebSocket connection error');
        setConnectionState('error');
        onError?.(event);
      };

    } catch (error) {
      setIsConnecting(false);
      setConnectionState('error');
      setError(error instanceof Error ? error.message : 'Failed to create WebSocket connection');
    }
  }, [
    token,
    buildWebSocketUrl,
    handleMessage,
    startHeartbeat,
    stopHeartbeat,
    clearTimeouts,
    onOpen,
    onClose,
    onError,
    autoReconnect,
    reconnectAttempts,
    maxReconnectAttempts,
    attemptReconnect,
  ]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    isManuallyDisconnected.current = true;
    clearTimeouts();
    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    setConnectionState('disconnected');
    setReconnectAttempts(0);
  }, [clearTimeouts, stopHeartbeat]);

  // Send message
  const sendMessage = useCallback((type: string, data: any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket is not connected');
      return;
    }

    try {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString(),
      };

      wsRef.current.send(JSON.stringify(message));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to send message');
    }
  }, []);

  // Auto-connect on mount if token is available
  useEffect(() => {
    if (token && !wsRef.current) {
      connect();
    }
  }, [token, connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    // Connection state
    isConnected,
    isConnecting,
    connectionState,
    error,
    
    // Actions
    connect,
    disconnect,
    sendMessage,
    
    // Message handling
    lastMessage,
    messageHistory,
    
    // Connection stats
    reconnectAttempts,
    lastReconnectTime,
  };
};

// Hook for optimization-specific WebSocket connection
export const useOptimizationWebSocket = (options: Omit<WebSocketOptions, 'onMessage'> = {}) => {
  const webSocket = useWebSocket('/optimization', {
    ...options,
    onMessage: (message) => {
      // Handle optimization-specific messages
      switch (message.type) {
        case 'optimization_started':
          console.log('Optimization started:', message.data);
          break;
        case 'optimization_stopped':
          console.log('Optimization stopped:', message.data);
          break;
        case 'optimization_error':
          console.error('Optimization error:', message.data);
          break;
      }
      
      options.onMessage?.(message);
    },
  });

  // Optimization-specific actions
  const startOptimizationMonitoring = useCallback((jobId: string) => {
    webSocket.sendMessage('subscribe_optimization', { jobId });
  }, [webSocket.sendMessage]);

  const stopOptimizationMonitoring = useCallback((jobId: string) => {
    webSocket.sendMessage('unsubscribe_optimization', { jobId });
  }, [webSocket.sendMessage]);

  return {
    ...webSocket,
    startOptimizationMonitoring,
    stopOptimizationMonitoring,
  };
};