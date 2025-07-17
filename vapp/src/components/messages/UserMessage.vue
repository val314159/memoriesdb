<template>
  <BaseMessage
    :message="message"
    kind="userMessage"
    class="user-message"
  >
    <template #default="{ message }">
      <div class="chat-meta">
        <span class="username">{{ message.username || 'Anonymous' }}</span>
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

const props = defineProps({
  message: {
    type: Object,
    required: true,
    default: () => ({
      username: 'Anonymous',
      content: '',
      timestamp: new Date().toISOString(),
      reactions: []
    })
  }
});
</script>

<style scoped>
.user-message {
  --border-color: rgba(76, 175, 80, 0.5);
  --glow-color: rgba(76, 175, 80, 0.1);
  margin: 0.5rem 0;
}

.user-message.is-own {
  --border-color: rgba(33, 150, 243, 0.7);
  --glow-color: rgba(33, 150, 243, 0.1);
  margin-left: 2rem;
}

.chat-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  font-size: 0.85rem;
}

.username {
  font-weight: 600;
  color: var(--text-primary);
}

.role-badge {
  font-size: 0.7em;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.1em 0.5em;
  border-radius: 1em;
  opacity: 0.8;
}

.chat-content {
  line-height: 1.5;
  word-break: break-word;
}

.reactions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.reaction {
  background: rgba(255, 255, 255, 0.1);
  padding: 0.1em 0.5em;
  border-radius: 1em;
  font-size: 0.9em;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reaction:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}
</style>
