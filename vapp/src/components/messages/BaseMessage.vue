<template>
  <Card 
    :class="[
      'group relative overflow-hidden transition-all',
      'hover:border-primary/30',
      isSelected && 'ring-2 ring-primary/50',
      customClass
    ]"
  >
    <CardContent class="p-4">
      <div class="flex gap-3" @click="toggleSelect">
        <!-- Avatar -->
        <Avatar class="h-8 w-8 mt-0.5 flex-shrink-0">
          <AvatarImage :src="getAvatarUrl(kind)" />
          <AvatarFallback class="text-xs">
            {{ kind === 'user' ? 'U' : kind === 'assistant' ? 'A' : 'S' }}
          </AvatarFallback>
        </Avatar>

        <!-- Message Content -->
        <div class="flex-1 space-y-2 min-w-0">
          <!-- Header with metadata -->
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium">
                {{ kind === 'user' ? 'You' : kind === 'assistant' ? 'Assistant' : 'System' }}
              </span>
              
              <TooltipProvider v-if="showTimestamp && message.timestamp">
                <Tooltip>
                  <TooltipTrigger as-child>
                    <span class="text-xs text-muted-foreground">
                      {{ formatTimestamp(message.timestamp) }}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <div class="flex items-center gap-1">
                      <IconClock class="h-3 w-3 mr-1" />
                      {{ new Date(message.timestamp).toLocaleString() }}
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>

            <!-- Message actions dropdown -->
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  class="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                  @click.stop
                >
                  <IconMoreHorizontal class="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" class="w-40">
                <DropdownMenuItem @click.stop="$emit('reply', message)">
                  <IconReply class="mr-2 h-4 w-4" />
                  <span>Reply</span>
                </DropdownMenuItem>
                <DropdownMenuItem @click.stop="$emit('react', message, '👍')">
                  <span class="mr-2">👍</span>
                  <span>Like</span>
                </DropdownMenuItem>
                <DropdownMenuItem @click.stop="$emit('react', message, '❤️')">
                  <span class="mr-2">❤️</span>
                  <span>Love</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  class="text-destructive focus:text-destructive"
                  @click.stop="$emit('delete', message)"
                >
                  <IconTrash class="mr-2 h-4 w-4" />
                  <span>Delete</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <!-- Message content -->
          <div class="prose prose-sm max-w-none">
            <slot :message="message"></slot>
          </div>

          <!-- Quick reactions -->
          <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button 
              variant="outline" 
              size="xs"
              class="h-6 text-xs px-2"
              @click.stop="$emit('react', message, '👍')"
            >
              <span class="mr-1">👍</span>
              Like
            </Button>
            <Button 
              variant="outline" 
              size="xs"
              class="h-6 text-xs px-2"
              @click.stop="$emit('react', message, '❤️')"
            >
              <span class="mr-1">❤️</span>
              Love
            </Button>
            <Button 
              variant="outline" 
              size="xs"
              class="h-6 text-xs px-2"
              @click.stop="$emit('reply', message)"
            >
              <IconReply class="h-3.5 w-3.5 mr-1" />
              Reply
            </Button>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { computed } from 'vue';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { 
  Clock as IconClock,
  User as IconUser,
  Bot as IconBot,
  Info as IconInfo,
  Reply as IconReply,
  MoreHorizontal as IconMoreHorizontal,
  Trash as IconTrash,
} from 'lucide-vue-next';

const props = defineProps({
  message: {
    type: Object,
    required: true
  },
  kind: {
    type: String,
    default: 'default',
    validator: (value) => ['user', 'assistant', 'system', 'default'].includes(value)
  },
  showTimestamp: {
    type: Boolean,
    default: true
  },
  customClass: {
    type: String,
    default: ''
  },
  isSelected: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['select', 'deselect', 'delete', 'reply', 'react']);

const toggleSelect = () => {
  if (props.isSelected) {
    emit('deselect', props.message);
  } else {
    emit('select', props.message);
  }
};

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const getBadgeVariant = (kind) => {
  switch (kind) {
    case 'user':
      return 'default';
    case 'assistant':
      return 'secondary';
    default:
      return 'outline';
  }
};

const getAvatarUrl = (kind) => {
  // You can replace these with actual avatar URLs
  const avatars = {
    user: '/avatars/user.png',
    assistant: '/avatars/assistant.png',
    system: '/avatars/system.png'
  };
  return avatars[kind] || '';
};
</script>

<style scoped>
/* Custom styles for message component */
:deep(.prose) {
  margin: 0;
  line-height: 1.5;
  color: inherit;
}

:deep(.prose p) {
  margin: 0;
  padding: 0;
}

:deep(.prose a) {
  color: var(--primary);
  text-decoration: none;
  font-weight: 500;
}

:deep(.prose a:hover) {
  text-decoration: underline;
  text-underline-offset: 2px;
}

:deep(.prose pre) {
  background-color: hsl(var(--muted));
  border-radius: var(--radius);
  padding: 0.75rem;
  margin: 0.5rem 0;
  overflow-x: auto;
  font-size: 0.875rem;
  line-height: 1.5;
}

:deep(.prose code) {
  background-color: hsl(var(--muted));
  border-radius: 0.25rem;
  padding: 0.2em 0.4em;
  font-size: 0.9em;
  font-family: var(--font-mono);
}

:deep(.prose pre code) {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 0.9em;
}

:deep(.prose ul),
:deep(.prose ol) {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}

:deep(.prose li) {
  margin: 0.25rem 0;
}

:deep(.prose h1),
:deep(.prose h2),
:deep(.prose h3) {
  margin: 1rem 0 0.5rem;
  line-height: 1.3;
  font-weight: 600;
}

:deep(.prose h1) {
  font-size: 1.5rem;
}

:deep(.prose h2) {
  font-size: 1.25rem;
}

:deep(.prose h3) {
  font-size: 1.1rem;
}

:deep(.prose blockquote) {
  margin: 0.5rem 0;
  padding: 0 0 0 1rem;
  border-left: 3px solid hsl(var(--border));
  color: hsl(var(--muted-foreground));
  font-style: italic;
}

/* Animation for message appearance */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-in {
  animation: fadeIn 0.15s ease-out forwards;
}

/* Custom scrollbar for code blocks */
:deep(::-webkit-scrollbar) {
  width: 6px;
  height: 6px;
}

:deep(::-webkit-scrollbar-track) {
  background: hsl(var(--muted));
  border-radius: 3px;
}

:deep(::-webkit-scrollbar-thumb) {
  background: hsl(var(--border));
  border-radius: 3px;
}

:deep(::-webkit-scrollbar-thumb:hover) {
  background: hsl(var(--border) / 0.8);
}
</style>
