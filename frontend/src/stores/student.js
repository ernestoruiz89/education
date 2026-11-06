import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createResource } from 'frappe-ui'

export const studentStore = defineStore('education-student', () => {
  const studentInfo = ref({})
  const currentProgram = ref({})
  const studentGroups = ref([])
  const loadError = ref(false)
  const student = createResource({
    url: 'education.api.student_portal.get_dashboard',
    onSuccess(data) {
      loadError.value = false
      studentInfo.value = data.student || {}
      currentProgram.value = data.enrollments?.[0] || {}
      studentGroups.value = (data.batches || []).map((batch) => ({
        ...batch,
        label: batch.batch_name || batch.name,
      }))
    },
    onError() {
      loadError.value = true
      studentInfo.value = {}
      currentProgram.value = {}
      studentGroups.value = []
    },
  })

  return {
    student,
    studentInfo,
    currentProgram,
    studentGroups,
    loadError,
    getStudentInfo: () => studentInfo,
    getCurrentProgram: () => currentProgram,
    getStudentGroups: () => studentGroups,
  }
})
