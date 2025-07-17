<template>
  <BaseMessage
    :message="message"
    kind="system"
    :class="[
      'tool-result-message',
      isError ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'
    ]"
  >
    <template #default="{ message }">
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0 mt-1">
          <div :class="[
            'h-2 w-2 rounded-full',
            isError ? 'bg-red-500' : 'bg-green-500'
          ]"></div>
        </div>
        <div class="space-y-1 flex-1 min-w-0">
          <div class="font-medium text-sm">
            <template v-if="isError">
              ❌ Tool error: {{ message.toolName || 'Tool call failed' }}
            </template>
            <template v-else>
              ✓ {{ message.toolName ? `${message.toolName} completed` : 'Tool completed' }}
            </template>
          </div>
          
          <div v-if="message.content" class="text-sm">
            {{ message.content }}
          </div>
          
          <div v-if="message.toolResult" class="mt-2 text-xs bg-muted/50 p-2 rounded">
            <pre class="whitespace-pre-wrap break-words">{{ formatToolResult(message.toolResult) }}</pre>
          </div>
        </div>
      </div>
    </template>
  </BaseMessage>
</template>

<script setup>
import BaseMessage from './BaseMessage.vue';
import { computed } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true,
    default: () => ({
      toolName: '',
      toolResult: null,
      isError: false
    })
  }
});

const isError = computed(() => props.message.isError || props.message.kind === 'error');

const formatToolResult = (result) => {
  if (typeof result === 'string') return result;
  try {
    return JSON.stringify(result, null, 2);
  } catch (e) {
    return String(result);
  }
};
</script>
