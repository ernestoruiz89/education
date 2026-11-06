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
import { __, formatDate, formatNumber } from '@/i18n'
import { computed } from 'vue'
import { ListView } from 'frappe-ui'
import { studentStore } from '@/stores/student'
import MissingData from '@/components/MissingData.vue'

const portal = studentStore()
const columns = [
  { label: __('Assessment'), key: 'assessment_name' },
  { label: __('Date'), key: 'date_label' },
  { label: __('Course'), key: 'course' },
  { label: __('Subject'), key: 'subject' },
  { label: __('Batch'), key: 'student_batch' },
  { label: __('Score'), key: 'result' },
  { label: __('Percentage'), key: 'percentage_label' },
]
const rows = computed(() =>
  (portal.student.data?.grades || []).map((row) => ({
    ...row,
    date_label: formatDate(row.schedule_date),
    result: `${formatNumber(row.score)} / ${formatNumber(row.maximum_score)}`,
    percentage_label: formatNumber(Number(row.percentage || 0) / 100, {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
  }))
)
</script>
