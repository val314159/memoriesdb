<script setup>
import { ref, onMounted, computed } from 'vue';
import { useWebSocket } from './composables/useWebSocket';
import MessagesContainer from './components/MessagesContainer.vue';

const messageText = ref('');
const ws = useWebSocket(import.meta.env.VITE_WS_BASE + import.meta.env.VITE_WS_PATH);

// Auto-connect when component mounts
onMounted(() => {
  ws.connect();
  
  // Add a welcome message
  ws.addMessage({
    id: 'welcome-msg',
    kind: 'system',
    content: 'Welcome to the chat!',
    timestamp: new Date().toISOString()
  });  
});

// Handle sending a new message
const sendMessage = () => {
  const text = messageText.value.trim();
  if (!text) return;
  
  // Create user message
  const userMessage = {
    id: `msg-${Date.now()}`,
    kind: 'userMessage',
    username: 'You',
    content: text,
    timestamp: new Date().toISOString(),
    status: 'sending'
  };
  
  // Add to local state immediately
  ws.addMessage(userMessage);
  
  // Send to WebSocket
  ws.send({
    kind: 'userMessage',
    content: text,
    timestamp: userMessage.timestamp,
    id: userMessage.id
  });
  
  // Simulate assistant response (replace with actual WebSocket response)
  setTimeout(() => {
    const assistantMessage = {
      id: `msg-${Date.now()}`,
      kind: 'assistant',
      username: 'Assistant',
      content: `Echo: ${text}`,
      timestamp: new Date().toISOString()
    };
    ws.addMessage(assistantMessage);
  }, 500);
  
  // Clear input
  messageText.value = '';
};

// Handle message deletion
const handleDeleteMessage = (message) => {
  console.log('Delete message:', message);
  // In a real app, you might want to send a delete request to the server
  // ws.send({
  //   kind: 'delete_message',
  //   messageId: message.id,
  //   timestamp: new Date().toISOString()
  // });
};
</script>

<template>
  <div class="flex flex-col h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm p-4">
      <div class="container mx-auto flex items-center justify-between">
        <h1 class="text-xl font-bold">Chat App</h1>
        <div class="flex items-center">
          <div class="w-3 h-3 rounded-full mr-2" :class="ws.isConnected.value ? 'bg-green-500' : 'bg-red-500'"></div>
          <span class="text-sm">{{ ws.isConnected.value ? 'Connected' : 'Disconnected' }}</span>
        </div>
      </div>
    </header>
    
    <!-- Messages -->
    <main class="flex-1 overflow-hidden">
      <div class="h-full container mx-auto p-4 flex flex-col">
        <MessagesContainer 
          :messages="ws.messages.value" 
          :is-connected="ws.isConnected.value"
          @delete="handleDeleteMessage"
          class="flex-1 overflow-y-auto mb-4"
        />
        
        <!-- Message Input -->
        <div class="bg-white rounded-lg shadow-md p-4">
          <div class="flex gap-2">
            <input 
              v-model="messageText"
              @keyup.enter="sendMessage"
              class="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Type a message..."
            />
            <button 
              @click="sendMessage"
              class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              :disabled="!messageText.trim()"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style>
/* Global styles can go here */
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Smooth scrolling for the messages container */
.messages-container {
  scroll-behavior: smooth;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
