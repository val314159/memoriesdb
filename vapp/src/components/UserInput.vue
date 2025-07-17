<template>
  <div class="bg-white rounded-lg shadow-md p-4">
    <form @submit.prevent="handleSubmit" class="flex gap-2">
      <Input
        ref="inputRef"
        v-model="inputText"
        placeholder="Type a message..."
        class="flex-1"
      />
      <Button 
        type="submit"
        :disabled="!inputText.trim()"
      >
        <IconSend class="h-4 w-4" />
        <span class="sr-only">Send</span>
      </Button>
    </form>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send as IconSend } from 'lucide-vue-next';

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['submit', 'update:modelValue']);

const inputText = ref(props.modelValue);
const inputRef = ref(null);

const handleSubmit = () => {
  if (!inputText.value.trim()) return;
  emit('submit', inputText.value);
  inputText.value = '';
  // Focus the input after sending
  nextTick(() => {
    const inputEl = inputRef.value?.$el?.querySelector('input');
    inputEl?.focus();
  });
};

// Update local value when prop changes
watch(() => props.modelValue, (newVal) => {
  if (newVal !== inputText.value) {
    inputText.value = newVal;
  }
});

// Emit update when input changes
watch(inputText, (newVal) => {
  emit('update:modelValue', newVal);
});

defineExpose({
  focus: () => inputRef.value?.focus()
});
</script>
