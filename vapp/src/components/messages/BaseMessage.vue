<template>
  <div 
    :class="['message', `message-${kind}`, customClass, { 'selected': isSelected }]"
    :style="messageStyle"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
    @click="toggleSelect"
  >
    <div class="message-inner" :class="{ 'message-hover': isHovered }">
      <div class="message-checkbox" @click.stop>
        <input 
          type="checkbox" 
          :checked="isSelected"
          @change="toggleSelect"
          class="checkbox checkbox-xs"
        />
      </div>
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
import { ref, computed, watch } from 'vue';

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

const emit = defineEmits(['reply', 'react', 'select', 'deselect', 'delete']);

const isHovered = ref(false);
const isSelected = ref(false);

const toggleSelect = () => {
  isSelected.value = !isSelected.value;
  if (isSelected.value) {
    emit('select', props.message);
  } else {
    emit('deselect', props.message);
  }
};

// Watch for external selection changes
watch(() => props.message.selected, (newVal) => {
  isSelected.value = newVal;
});

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
/* Base message container - absolutely positioned to prevent layout shifts */
.message {
  position: relative;
  min-height: 80px; /* Fixed minimum height */
  margin: 0.5rem 0;
  padding-left: 2rem; /* Space for checkbox */
  border-left: 2px solid transparent;
  transition: border-color 0.2s ease;
}

.message.selected {
  border-left-color: #3b82f6;
  background-color: #f8fafc;
}

/* Checkbox - absolutely positioned */
.message-checkbox {
  position: absolute;
  left: 0.5rem;
  top: 0.75rem;
  width: 24px;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
  z-index: 1;
}

.message:hover .message-checkbox,
.message.selected .message-checkbox,
.message:focus-within .message-checkbox {
  opacity: 1;
  pointer-events: auto;
}

/* Message inner - takes full width */
.message-inner {
  position: relative;
  min-height: 60px;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  background: var(--message-bg, white);
  border: 1px solid var(--border-color, #e5e7eb);
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
}

/* Actions container - absolutely positioned at the bottom */
.message-actions {
  position: absolute;
  bottom: 0.5rem;
  left: 1rem;
  right: 1rem;
  display: flex;
  gap: 0.5rem;
  opacity: 0;
  transform: translateY(5px);
  transition: all 0.2s ease;
  pointer-events: none;
  justify-content: flex-end;
  background: linear-gradient(to top, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0) 100%);
  padding: 1rem 0 0.25rem;
  margin: 0 -0.5rem -0.5rem;
  border-radius: 0 0 0.5rem 0.5rem;
}

/* Show actions on hover */
.message-inner:hover .message-actions,
.message-inner:focus-within .message-actions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

/* Hide actions if empty */
.message-actions:empty {
  display: none;
}

/* Ensure content has enough padding to avoid overlap with actions */
.content {
  padding-bottom: 1.5rem; /* Space for actions */
  position: relative;
  z-index: 0;
}

/* Timestamp styling */
.timestamp {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-bottom: 0.25rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
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
