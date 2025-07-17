<template>
  <BaseMessage
    :message="message"
    kind="assistant"
    class="assistant-message"
  >
    <template #default="{ message }">
      <div class="chat-meta">
        <span class="username">{{ message.username || 'Assistant' }}</span>
        <span v-if="message.role" class="role-badge">{{ message.role }}</span>
      </div>
      <div class="chat-content">
        {{ message.content }}
      </div>
      <div v-if="message.reactions?.length" class="reactions">
        <span 
          v-for="(reaction, index) in message.reactions" 
          :key="index"
          class="reaction"
        >
          {{ reaction }}
        </span>
      </div>
    </template>
  </BaseMessage>
</template>

<script setup>
import BaseMessage from './BaseMessage.vue';

defineProps({
  message: {
    type: Object,
    required: true
  }
});
</script>

<style scoped>
.assistant-message {
  --border-color: rgba(156, 163, 175, 0.5);
  --glow-color: rgba(156, 163, 175, 0.1);
  margin: 0.5rem 0;
  margin-right: 2rem;
}

.assistant-message .username {
  color: #6b7280;
  font-weight: 600;
}

.assistant-message .chat-content {
  color: #1f2937;
  line-height: 1.5;
}

.role-badge {
  background-color: #e5e7eb;
  color: #4b5563;
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  margin-left: 0.5rem;
}
</style>
