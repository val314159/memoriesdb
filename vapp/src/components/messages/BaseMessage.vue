<template>
  <div 
    :class="['message', `message-${kind}`, customClass]"
    :style="messageStyle"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="message-inner" :class="{ 'message-hover': isHovered }">
      <div v-if="showTimestamp && message.timestamp" class="timestamp">
        <span class="time-icon">⏱️</span>
        <span class="time-text">{{ formatTimestamp(message.timestamp) }}</span>
      </div>
      <div class="content">
        <slot :message="message"></slot>
      </div>
      <transition name="fade">
        <div v-if="isHovered" class="message-actions">
          <button class="btn btn-ghost btn-xs" @click.stop="$emit('reply', message)">
            <span class="icon">↩️</span> Reply
          </button>
          <button class="btn btn-ghost btn-xs" @click.stop="$emit('react', message, '👍')">
            👍
          </button>
          <button class="btn btn-ghost btn-xs" @click.stop="$emit('react', message, '❤️')">
            ❤️
          </button>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  kind: {
    type: String,
    default: 'default'
  },
  showTimestamp: {
    type: Boolean,
    default: true
  },
  customClass: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['reply', 'react']);

const isHovered = ref(false);

const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

const messageStyle = computed(() => {
  if (props.message.priority === 'high') {
    return {
      '--glow-color': 'rgba(255, 82, 82, 0.3)',
      '--border-color': 'rgba(255, 82, 82, 0.5)'
    };
  }
  return {};
});
</script>

<style scoped>
.message {
  --glow-color: rgba(0, 150, 255, 0.1);
  --border-color: rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  margin: 0.5rem 0;
  border-radius: 0.5rem;
  overflow: hidden;
  position: relative;
}

.message-inner {
  padding: 0.75rem 1rem;
  border-left: 4px solid var(--border-color);
  background: rgba(255, 255, 255, 0.03);
  transition: all 0.2s ease;
}

.message-hover {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 2px 8px -1px var(--glow-color);
}

.timestamp {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.message-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-system {
  --border-color: rgba(100, 181, 246, 0.7);
}

.message-chat {
  --border-color: rgba(76, 175, 80, 0.7);
}

.message-error {
  --border-color: rgba(244, 67, 54, 0.7);
  --glow-color: rgba(244, 67, 54, 0.2);
}

@keyframes popIn {
  0% { transform: scale(0.95); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.message-enter-active {
  animation: popIn 0.3s cubic-bezier(0.2, 0, 0.2, 1);
}

.btn-ghost {
  transition: all 0.2s ease;
  opacity: 0.7;
}

.btn-ghost:hover {
  opacity: 1;
  transform: scale(1.1);
}

@media (max-width: 640px) {
  .message-inner {
    padding: 0.5rem;
  }
  
  .message-actions {
    gap: 0.25rem;
  }
}
</style>
