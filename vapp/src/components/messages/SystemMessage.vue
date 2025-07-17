<template>
  <BaseMessage
    :message="message"
    kind="system"
    class="system-message"
  >
    <template #default="{ message }">
      <div class="system-content">
        <span class="system-icon">ℹ️</span>
        <span class="text">{{ message.content }}</span>
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
.system-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.system-icon {
  font-size: 1.1em;
  opacity: 0.8;
}

.system-message {
  --border-color: rgba(100, 181, 246, 0.7);
  --glow-color: rgba(100, 181, 246, 0.1);
}
</style>
