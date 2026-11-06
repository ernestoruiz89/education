<template>
  <main
    class="min-h-screen bg-gray-50 flex items-center justify-center px-5 py-12"
  >
    <div class="w-full max-w-xl rounded-xl border bg-white p-8 shadow-sm">
      <img
        v-if="portal.student.data?.school?.logo"
        :src="portal.student.data.school.logo"
        :alt="__('School logo')"
        class="h-20 w-20 object-contain mb-6"
      />
      <p class="text-base text-gray-600 mb-3">
        {{ portal.student.data?.school?.name || 'Education' }} ·
        {{ __('Student portal') }}
      </p>
      <h1 class="text-2xl font-semibold text-gray-900 mb-4">
        {{
          __(
            portal.loadError
              ? 'Unable to load the portal'
              : 'Your account has no linked student'
          )
        }}
      </h1>
      <p class="text-base leading-7 text-gray-700 mb-6">
        {{
          __(
            portal.loadError
              ? 'Try again. If your session expired, please sign in again.'
              : 'This portal shows your schedule, grades, attendance and invoices. Ask the administration to link your account to the corresponding student.'
          )
        }}
      </p>
      <p v-if="user.data?.email" class="text-base text-gray-600 mb-6">
        {{ __('Account') }}: {{ user.data.email }}
      </p>
      <div class="flex flex-wrap gap-3">
        <a
          v-if="user.data?.user_type === 'System User'"
          href="/desk"
          class="rounded bg-gray-900 px-4 py-2.5 text-base text-white"
        >
          {{ __('Open Desk') }}
        </a>
        <Button
          :loading="portal.student.loading || user.loading"
          :label="__('Try again')"
          @click="retry"
        />
        <Button
          :loading="logout.loading"
          :label="__('Log out')"
          @click="logout.submit()"
        />
      </div>
    </div>
  </main>
</template>

<script setup>
import { __ } from '@/i18n'
import { useRouter } from 'vue-router'
import { studentStore } from '@/stores/student'
import { usersStore } from '@/stores/user'
import { sessionStore } from '@/stores/session'

const portal = studentStore()
const { user } = usersStore()
const { logout } = sessionStore()
const router = useRouter()
async function retry() {
  try {
    await user.reload()
    await portal.student.reload()
    if (portal.studentInfo.name) await router.replace('/schedule')
  } catch {
    portal.loadError = true
  }
}
</script>
