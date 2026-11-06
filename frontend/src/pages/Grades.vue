<template>
  <div v-if="rows.length" class="px-5 py-4 overflow-x-auto">
    <ListView
      :columns="columns"
      :rows="rows"
      :options="{ selectable: false, showTooltip: false }"
      row-key="name"
    />
  </div>
  <MissingData v-else message="No grades found" />
</template>

<script setup>
import { computed } from 'vue'
import { ListView } from 'frappe-ui'
import { studentStore } from '@/stores/student'
import MissingData from '@/components/MissingData.vue'

const portal = studentStore()
const columns = [
  { label: 'Assessment', key: 'assessment_name' },
  { label: 'Date', key: 'schedule_date' },
  { label: 'Course', key: 'course' },
  { label: 'Subject', key: 'subject' },
  { label: 'Batch', key: 'student_batch' },
  { label: 'Score', key: 'result' },
  { label: 'Percentage', key: 'percentage_label' },
]
const rows = computed(() =>
  (portal.student.data?.grades || []).map((row) => ({
    ...row,
    result: `${row.score ?? 0} / ${row.maximum_score ?? 0}`,
    percentage_label: `${Number(row.percentage || 0).toFixed(2)}%`,
  }))
)
</script>
