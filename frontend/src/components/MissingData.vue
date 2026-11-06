<template lang="">
  <div class="flex items-center justify-center h-[250px]">
    <p class="text-gray-500">{{ __(message) }}</p>
  </div>
</template>
<script setup>
import { __ } from '@/i18n'
const props = defineProps({
  message: {
    type: String,
    default: 'No data found',
  },
})
</script>
