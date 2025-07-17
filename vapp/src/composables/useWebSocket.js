import { ref, onUnmounted } from 'vue';

const str = JSON.stringify;

export function useWebSocket(url) {
  const isConnected = ref(false);
  const lastError = ref(null);
  const messages = ref([]);
  let socket = null;
  
  // Message handlers - can be extended by the consumer
  const handlers = {
    // Default handler for unhandled message kinds
    _default(message) {
      console.log('Unhandled message kind:', message.kind, message);
      messages.value.push(message);
    },
    
    // Example handler - can be overridden
    initialize(message) {
	console.log('Initialize message received:', message);
	messages.value.push(message);
    },
    
    // Example handler - can be overridden
    chat_message(message) {
      console.log('Chat message received:', message);
      messages.value.push(message);
    },
    
    // System messages
    system(message) {
      console.log('System message:', message);
      messages.value.push(message);
    }
  };

  const connect = () => {
    try {
      socket = new WebSocket(url);

      socket.onopen = () => {
        console.log('WebSocket connected');
        isConnected.value = true;
        lastError.value = null;
      };

      const handleMessage = (message) => {
        try {
          // Call the appropriate handler based on message kind
            const handler = handlers[message.kind] || handlers[message.method] || handlers._default;
          handler(message);
        } catch (error) {
          console.error('Error in message handler:', error);
          lastError.value = error;
        }
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (!message.kind)
            console.warn('Message missing kind:', message);
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing message:', error, event.data);
          lastError.value = error;
        }
      };

      socket.onclose = () => {
        isConnected.value = false;
      };

      socket.onerror = (error) => {
        lastError.value = error || new Error('WebSocket connection error');
      };

    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      lastError.value = error;
    }
  };

  const send = (data) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return false;
    }
    
    try {
      const message = typeof data === 'string' ? data : JSON.stringify({
        ...data,
        timestamp: data.timestamp || new Date().toISOString()
      });
      socket.send(message);
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      lastError.value = error;
      return false;
    }
  };

  // Register a new message handler
  const on = (kind, handler) => {
    handlers[kind] = handler;
    // Return cleanup function
    return () => delete handlers[kind];
  };

  // Clean up on unmount
  onUnmounted(() => {
    if (socket) {
      socket.close();
    }
  });

  return {
    isConnected,
    lastError,
    messages,
    send,
    connect,
    on, // Add the ability to register handlers
    handlers // Expose handlers for direct manipulation if needed
  };
}
