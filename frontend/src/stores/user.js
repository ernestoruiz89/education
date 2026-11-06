import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

export const usersStore = defineStore('education-users', () => {
  const user = createResource({
    url: 'education.education.api.get_user_info',
    initialData: [],
  })

  return {
    user,
  }
})
