<template>
  <div v-if="rows.length" class="px-5 py-4">
    <p
      v-if="!portal.student.data.payment_enabled"
      class="mb-4 text-base text-gray-600"
    >
      Online payment is not configured. Contact the academy to pay an invoice.
    </p>
    <ListView
      :columns="columns"
      :rows="rows"
      :options="{ selectable: false, showTooltip: false }"
      row-key="name"
    >
      <ListHeader>
        <ListHeaderItem
          v-for="column in columns"
          :key="column.key"
          :item="column"
        />
      </ListHeader>
      <ListRow
        v-for="row in rows"
        :key="row.name"
        :row="row"
        v-slot="{ column, item }"
      >
        <ListRowItem :item="item" :align="column.align">
          <Badge
            v-if="column.key === 'status'"
            variant="subtle"
            :theme="badgeColor(row.status)"
            :label="item"
          />
          <div v-else-if="column.key === 'cta'" class="flex gap-2">
            <Button
              v-if="row.can_print"
              @click="openInvoicePDF(row)"
              icon-left="download"
              label="Invoice PDF"
            />
            <Button
              v-if="
                portal.student.data.payment_enabled &&
                row.outstanding_amount > 0
              "
              @click="openModal(row)"
              icon-left="credit-card"
              label="Pay Now"
            />
            <span
              v-if="!row.can_print && !portal.student.data.payment_enabled"
              class="text-gray-600"
              >Contact the academy</span
            >
          </div>
          <span v-else>{{ item }}</span>
        </ListRowItem>
      </ListRow>
    </ListView>
    <FeesPaymentDialog
      v-if="currentRow && showPaymentDialog"
      :row="currentRow"
      :student="portal.studentInfo"
      v-model="showPaymentDialog"
      @success="success"
    />
  </div>
  <MissingData v-else message="No invoices found" />
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRow,
  ListRowItem,
  Badge,
} from 'frappe-ui'
import FeesPaymentDialog from '@/components/FeesPaymentDialog.vue'
import { studentStore } from '@/stores/student'
import MissingData from '@/components/MissingData.vue'
import { createToast } from '@/utils'

const portal = studentStore()
const money = (value, currency) =>
  new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(
    Number(value || 0)
  )
const rows = computed(() =>
  (portal.student.data?.invoices || []).map((row) => ({
    ...row,
    invoice: row.name,
    amount: money(row.outstanding_amount, row.currency),
    total: money(row.grand_total, row.currency),
  }))
)
const columns = [
  { label: 'Invoice', key: 'name' },
  { label: 'Status', key: 'status' },
  { label: 'Due Date', key: 'due_date' },
  { label: 'Total', key: 'total' },
  { label: 'Outstanding', key: 'amount' },
  { label: 'Actions', key: 'cta', width: 2 },
]
const currentRow = ref(null)
const showPaymentDialog = ref(false)
function openInvoicePDF(row) {
  const params = new URLSearchParams({
    doctype: 'Sales Invoice',
    name: row.name,
    format: portal.student.data.print_format || 'Standard',
  })
  window.open(
    '/api/method/frappe.utils.print_format.download_pdf?' + params,
    '_blank',
    'noopener'
  )
}
function openModal(row) {
  currentRow.value = row
  showPaymentDialog.value = true
}
async function success() {
  await portal.student.reload()
  createToast({
    title: 'Payment successful',
    icon: 'check',
    iconClasses: 'text-green-600',
  })
}
const badgeColor = (status) =>
  ({ Paid: 'green', Unpaid: 'red', Overdue: 'red', 'Partly Paid': 'orange' }[
    status
  ] || 'gray')
</script>
