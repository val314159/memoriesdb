<template>
  <div class="messages-container">
    <div v-for="(messageGroup, date) in groupedMessages" :key="date" class="message-group">
      <div class="date-divider">
        <span class="date-text">{{ date }}</span>
      </div>
      
      <TransitionGroup 
        name="message" 
        tag="div" 
        class="space-y-2"
      >
        <component
          v-for="message in messageGroup"
          :key="message.id || message.timestamp"
          :is="getMessageComponent(message)"
          :message="message"
          :class="{
            'message-important': message.priority === 'high',
            'message-unread': !message.read,
            'message-sending': message.status === 'sending'
          }"
          @reply="handleReply"
          @react="handleReaction"
        />
      </TransitionGroup>
    </div>
    
    <div v-if="!isConnected" class="connection-status">
      <div class="status-indicator"></div>
      <span>Connecting...</span>
    </div>
    
    <div v-if="lastError" class="error-message">
      {{ lastError.message }}
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { SystemMessage, UserMessage } from './messages';

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isConnected: {
    type: Boolean,
    default: false
  },
  lastError: {
    type: Error,
    default: null
  }
});

const emit = defineEmits(['reply', 'reaction']);

// Group messages by date
const groupedMessages = computed(() => {
  const groups = {};
  const today = new Date().toDateString();
  const yesterday = new Date(Date.now() - 86400000).toDateString();
  
  props.messages.forEach(message => {
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

const getMessageComponent = (message) => {
  switch (message.kind) {
    case 'system':
      return SystemMessage;
    case 'userMessage':
      return UserMessage;
    default:
      return 'div';
  }
};

const handleReply = (message) => {
  emit('reply', message);
};

const handleReaction = (message, reaction) => {
  emit('reaction', message, reaction);
};

// Auto-scroll to bottom when new messages arrive
const container = ref(null);

const scrollToBottom = () => {
  if (container.value) {
    container.value.scrollTop = container.value.scrollHeight;
  }
};

// Scroll to bottom when component mounts or updates
onMounted(() => {
  scrollToBottom();
  window.addEventListener('resize', scrollToBottom);
});

onUnmounted(() => {
  window.removeEventListener('resize', scrollToBottom);
});
</script>

<style scoped>
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  scroll-behavior: smooth;
}

.message-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.date-divider {
  display: flex;
  align-items: center;
  margin: 1rem 0;
  color: var(--text-secondary);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.date-divider::before,
.date-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background-color: var(--border-color);
  margin: 0 0.5rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 235, 59, 0.1);
  border-left: 3px solid #ffeb3b;
  border-radius: 0 4px 4px 0;
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ffeb3b;
  animation: pulse 1.5s infinite;
}

.error-message {
  padding: 0.5rem 1rem;
  background: rgba(244, 67, 54, 0.1);
  border-left: 3px solid #f44336;
  border-radius: 0 4px 4px 0;
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #f44336;
}

.message-sending {
  opacity: 0.7;
}

.message-important {
  animation: pulse 2s infinite;
}

.message-unread {
  border-left-color: #4caf50 !important;
  background: rgba(76, 175, 80, 0.05) !important;
}

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

/* Message transition animations */
.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-enter-from,
.message-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Ensure leaving items are taken out of layout flow */
.message-leave-active {
  position: absolute;
  width: 100%;
}

/* Custom scrollbar */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.3);
}
</style>
