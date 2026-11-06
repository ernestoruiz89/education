<template>
  <div class="py-4 flex flex-col">
    <div v-if="batches.length" class="px-5 mb-2 max-w-xl">
      <FormControl
        type="select"
        :label="__('Batch')"
        :options="batches"
        v-model="selectedBatch"
      />
    </div>
    <Calendar v-if="events.length" :events="events" />
    <MissingData v-else message="No attendance records for this batch" />
    <Dialog
      v-model="isAttendancePage"
      :options="{ title: __('Request Leave'), size: 'xl' }"
    >
      <template #body-content>
        <p class="text-base text-gray-600 mb-4">
          {{
            __(
              'Your request is saved for staff review. Attendance changes after approval.'
            )
          }}
        </p>
        <FormControl
          type="select"
          :label="__('Batch')"
          :options="batches.filter((b) => b.value)"
          v-model="leave.student_batch"
          class="mb-4"
        />
        <NewLeave :newLeave="leave" />
        <ErrorMessage :message="error" class="mt-4" />
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button
            :label="__('Cancel')"
            :disabled="request.loading"
            @click="close"
          />
          <Button
            :label="__('Send request')"
            variant="solid"
            :loading="request.loading"
            :disabled="!validLeave"
            @click="submitLeave"
          />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { __ } from '@/i18n'
import { computed, reactive, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Dialog, FormControl, ErrorMessage, createResource } from 'frappe-ui'
import { leaveStore } from '@/stores/leave'
import { studentStore } from '@/stores/student'
import NewLeave from '@/components/NewLeave.vue'
import Calendar from '@/components/Calendar.vue'
import MissingData from '@/components/MissingData.vue'
import { createToast } from '@/utils'

const portal = studentStore()
const { isAttendancePage } = storeToRefs(leaveStore())
const selectedBatch = ref('')
const batches = computed(() => [
  { label: __('All batches'), value: '' },
  ...portal.studentGroups.map((b) => ({ label: b.label, value: b.name })),
])
const statusColors = {
  Present: 'bg-green-100',
  Absent: 'bg-red-200',
  Leave: 'bg-orange-100',
}
const events = computed(() =>
  (portal.student.data?.attendance || [])
    .filter(
      (row) => !selectedBatch.value || row.student_batch === selectedBatch.value
    )
    .map((row) => ({
      name: row.name,
      title: `${__(row.status)}${
        row.student_batch ? ' · ' + row.student_batch : ''
      }`,
      background_color: statusColors[row.status],
      date: row.date,
      status: row.status,
    }))
)
const leave = reactive({
  student: portal.studentInfo.student_name,
  student_batch: '',
  from_date: '',
  to_date: '',
  reason: '',
  total_days: '',
})
const error = ref('')
watch(isAttendancePage, (open) => {
  if (open) {
    error.value = ''
    leave.student_batch =
      selectedBatch.value || portal.studentGroups[0]?.name || ''
  }
})
const validLeave = computed(
  () =>
    leave.student_batch &&
    leave.from_date &&
    leave.to_date &&
    leave.from_date <= leave.to_date &&
    leave.reason.trim()
)
const request = createResource({
  url: 'education.api.student_portal.request_leave',
})
async function submitLeave() {
  error.value = ''
  try {
    await request.submit({
      student_batch: leave.student_batch,
      from_date: leave.from_date,
      to_date: leave.to_date,
      reason: leave.reason,
    })
    isAttendancePage.value = false
    Object.assign(leave, {
      from_date: '',
      to_date: '',
      reason: '',
      total_days: '',
    })
    createToast({
      title: __('Leave request saved for staff review'),
      icon: 'check',
      iconClasses: 'text-green-600',
    })
  } catch (err) {
    error.value = __(
      err.messages?.[0] || err.message || 'Unable to save your request'
    )
  }
}
</script>
