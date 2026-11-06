<template>
  <div class="w-full h-full">
    <Calendar v-if="events.length" :events="events" />
    <MissingData v-else message="No classes scheduled for your enrollments" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Calendar from '@/components/Calendar.vue'
import MissingData from '@/components/MissingData.vue'
import { studentStore } from '@/stores/student'

const portal = studentStore()
const time = (value) =>
  value ? String(value).split('.')[0].padStart(8, '0').slice(0, 5) : ''
const events = computed(() =>
  (portal.student.data?.schedules || []).map((row) => ({
    title: row.title || row.subject || row.course,
    with: row.faculty_name,
    name: row.name,
    room: row.room,
    date: row.schedule_date,
    from_time: time(row.from_time),
    to_time: time(row.to_time),
    color: row.class_schedule_color,
  }))
)
</script>
