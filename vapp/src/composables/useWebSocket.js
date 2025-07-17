import { ref, onUnmounted, computed } from 'vue';

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
      addMessage({
        ...message,
        timestamp: message.timestamp || new Date().toISOString(),
      });
    },
    
    // System messages
    system(message) {
      console.log('System message:', message);
      addMessage({
        ...message,
        kind: 'system',
        timestamp: message.timestamp || new Date().toISOString(),
      });
    },
    
    // User messages (from any user)
    userMessage(message) {
      console.log('User message received:', message);
      addMessage({
        ...message,
        kind: 'userMessage',
        timestamp: message.timestamp || new Date().toISOString(),
        reactions: message.reactions || []
      });
    },
    
    // Initialize handshake
    initialize(message) {
      console.log('Initialize message received:', message);
      addMessage({
        ...message,
        kind: 'system',
        timestamp: message.timestamp || new Date().toISOString(),
        priority: 'high'
      });
    },
    
    // Error messages
    error(message) {
      console.error('Error message:', message);
      addMessage({
        ...message,
        kind: 'error',
        timestamp: message.timestamp || new Date().toISOString(),
        priority: 'high'
      });
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

  const addMessage = (message) => {
    // Ensure we don't add duplicate messages
    if (!messages.value.some(m => m.id === message.id || (m.timestamp === message.timestamp && m.content === message.content))) {
      messages.value.push(message);
    }
  };

  const send = (data) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return false;
    }
    
    try {
      const message = {
        ...(typeof data === 'string' ? { content: data } : data),
        timestamp: data?.timestamp || new Date().toISOString(),
        id: data?.id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      };
      
      // Set default values for user messages
      if (message.kind === 'userMessage' || !message.kind) {
        message.username = message.username || 'Anonymous';
        message.kind = 'userMessage';
      }
      
      socket.send(JSON.stringify(message));
      
      // For user messages, add to our local state immediately for instant feedback
      if (message.kind === 'userMessage') {
        addMessage({
          ...message,
          isOwn: true,
          status: 'sending'
        });
      }
      
      return true;
    } catch (error) {
      console.error('Error sending message:', error);
      lastError.value = error;
      return false;
    }
  };
  
  // Add reaction to a message
  const addReaction = (messageId, reaction) => {
    const message = messages.value.find(m => m.id === messageId);
    if (message) {
      message.reactions = message.reactions || [];
      if (!message.reactions.includes(reaction)) {
        message.reactions = [...message.reactions, reaction];
        
        // Send reaction to server
        send({
          kind: 'reaction',
          messageId,
          reaction,
          timestamp: new Date().toISOString()
        });
      }
    }
  };

  // Register a new message handler
  const on = (kind, handler) => {
    handlers[kind] = handler;
    // Return cleanup function
    return () => delete handlers[kind];
  };

  // Group messages by date
  const groupedMessages = computed(() => {
    const groups = {};
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    messages.value.forEach(message => {
      const date = new Date(message.timestamp);
      let dateStr;
      
      if (date.toDateString() === today) {
        dateStr = 'Today';
      } else if (date.toDateString() === yesterday) {
        dateStr = 'Yesterday';
      } else {
        dateStr = date.toLocaleDateString('en-US', { 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        });
      }
      
      if (!groups[dateStr]) {
        groups[dateStr] = [];
      }
      
      groups[dateStr].push(message);
    });
    
    return groups;
  });

  // Clean up on unmount
  onUnmounted(() => {
    if (socket) {
      socket.close();
    }
  });

  // Function to add a message directly (useful for local state updates)
  const addMessageExported = (message) => {
    messages.value = [...messages.value, {
      ...message,
      id: message.id || `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: message.timestamp || new Date().toISOString(),
      status: message.status || 'delivered'
    }];
  };

  return {
    isConnected,
    lastError,
    messages,
    groupedMessages,
    connect,
    disconnect: () => {
      if (socket) {
        socket.close();
        socket = null;
      }
      isConnected.value = false;
    },
    send,
    addMessage: addMessageExported,
    on,
    handlers
  };
}
