<script setup>
import { ref, onMounted } from 'vue';
import { useWebSocket } from './composables/useWebSocket';

const messageText = ref('');
const ws = useWebSocket(import.meta.env.VITE_WS_BASE+import.meta.env.VITE_WS_PATH);

// Auto-connect when component mounts
onMounted(() => {
  ws.connect();
});

const sendMessage = () => {
  if (messageText.value.trim()) {
    ws.send({
      kind: 'user_message',
      content: messageText.value,
      timestamp: new Date().toISOString()
    });
    messageText.value = '';
  }
};
</script>

<template>
  <div class="container mx-auto p-4">
    <div class="flex items-center mb-4">
      <div class="w-3 h-3 rounded-full mr-2" :class="ws.isConnected.value ? 'bg-green-500' : 'bg-red-500'"></div>
      <span>WebSocket: {{ ws.isConnected.value ? 'Connected' : 'Disconnected' }}</span>
    </div>
    
    <div class="mb-4">
      <h2 class="text-xl font-bold mb-2">Send Message</h2>
      <div class="flex gap-2">
        <input 
          v-model="messageText"
          @keyup.enter="sendMessage"
          class="flex-1 p-2 border rounded"
          placeholder="Type a message..."
        />
        <button 
          @click="sendMessage"
          class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          :disabled="!ws.isConnected.value"
        >
          Send
        </button>
      </div>
    </div>

    <div class="mt-6">
      <h2 class="text-xl font-bold mb-2">Received Messages</h2>
      <div v-if="ws.messages.value.length === 0" class="text-gray-500">
        No messages received yet
      </div>
      <div v-else class="space-y-2">
        <div 
          v-for="(msg, index) in ws.messages.value" 
          :key="index"
          class="p-3 border rounded bg-gray-50"
        >
          <pre class="text-sm">{{ JSON.stringify(msg, null, 2) }}</pre>
        </div>
      </div>
    </div>

    <div v-if="ws.lastError.value" class="mt-4 p-3 bg-red-100 text-red-700 rounded">
      Error: {{ ws.lastError.value.message }}
    </div>
  </div>
</template>
