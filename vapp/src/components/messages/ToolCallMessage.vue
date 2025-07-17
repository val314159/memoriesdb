<template>
  <BaseMessage
    :message="message"
    kind="tool-call"
    class="tool-call-message"
  >
    <template #default="{ message }">
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 mt-1">
          <div class="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></div>
        </div>
        <div class="space-y-1">
          <div class="font-medium text-sm">
            Calling tool: {{ message.toolName || 'External tool' }}
          </div>
          <div v-if="message.toolArgs" class="text-xs text-muted-foreground">
            <pre class="whitespace-pre-wrap">{{ formatToolArgs(message.toolArgs) }}</pre>
          </div>
        </div>
      </div>
    </template>
  </BaseMessage>
</template>

<script setup>
import BaseMessage from './BaseMessage.vue';

defineProps({
  message: {
    type: Object,
    required: true,
    default: () => ({
      toolName: '',
      toolArgs: {}
    })
  }
});

const formatToolArgs = (args) => {
  try {
    return JSON.stringify(args, null, 2);
  } catch (e) {
    return String(args);
  }
};
</script>
