<template lang="">
  <header
    class="flex justify-between gap-3 items-center px-5 py-2.5 h-12 border-b"
  >
    <div class="flex gap-2 items-center cursor-pointer">
      <h3 class="font-medium text-lg text-gray-900">
        {{ currentRoute }}
      </h3>
    </div>
    <div class="flex flex-row gap-2">
      <Button
        v-if="
          currentRoute === 'Attendance' &&
          portal.student.data?.can_request_leave
        "
        variant="solid"
        label="Apply for Leave"
        @click="setIsAttendancePage(true)"
        icon-left="plus"
      />
    </div>
  </header>
</template>
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { leaveStore } from '@/stores/leave'
import { studentStore } from '@/stores/student'

const router = useRouter()
const portal = studentStore()
const currentRoute = computed(() => router.currentRoute.value.name)

const { setIsAttendancePage } = leaveStore()
</script>
