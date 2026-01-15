<template>
  <div class="standart-table">
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th v-for="head in headers" :key="head">
              {{ formatHeader(head) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in data" :key="rowIndex">
            <td v-for="key in headers" :key="key" :class="getCellClass(key, row[key])">
              {{ formatValue(key, row[key]) }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="data.length === 0" class="no-data">
        No devices connected
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
})

const headers = computed(() =>
  props.data.length > 0 ? Object.keys(props.data[0]) : []
)

// Format header names (convert snake_case to Title Case)
function formatHeader(header) {
  return header
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// Format cell values
function formatValue(key, value) {
  if (value === null || value === undefined) return '-'

  // Format numbers with decimals
  if (typeof value === 'number' && !Number.isInteger(value)) {
    return value.toFixed(2)
  }

  // Format battery percentage
  if (key === 'battery' && typeof value === 'number') {
    return `${value}%`
  }

  return value
}

// Get cell-specific classes
function getCellClass(key, value) {
  const classes = []

  // Status-based coloring
  if (key === 'status') {
    classes.push(`status-${value}`)
  }

  // Battery warning
  if (key === 'battery' && typeof value === 'number') {
    if (value < 20) classes.push('battery-low')
    else if (value < 50) classes.push('battery-medium')
  }

  return classes.join(' ')
}
</script>

<style scoped>
.standart-table {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.table-wrapper {
  min-width: 100%;
  overflow-x: auto;
}

.data-table {
  font-family: 'Fira sans', sans-serif;
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  /* ✅ Force equal column widths */
  font-size: 0.875rem;
  text-align: center;
  background-color: #111827;
  color: #f3f4f6;
  border-radius: 0.5rem;
}

.data-table thead {
  background-color: #1f2937;
  color: #d1d5db;
}

.data-table th {
  padding: 0.5rem;
  border-right: 1px solid #374151;
  font-weight: 600;
  text-transform: capitalize;
}

.data-table th:last-child {
  border-right: none;
}

.data-table tbody tr {
  transition: background-color 0.2s;
}

.data-table tbody tr:hover {
  background-color: #1f2937;
}

.data-table td {
  padding: 0.5rem;
  border-top: 1px solid #374151;
}

.data-table td,
.data-table th {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}



/* Status colors */
.status-connected {
  color: #10b981;
  font-weight: 600;
}

.status-standby {
  color: #06b6d4;
  font-weight: 600;
}

.status-locked {
  color: #ef4444;
  font-weight: 600;
}

.status-cup {
  color: #10b981;
  font-weight: 600;
}

.status-invalid_cup {
  color: #ef4444;
  font-weight: 600;
}

/*#06b6d4*/
.status-active {
  color: #ef4444;
  font-weight: 600;
}

.status-ready {
  color: #8b5cf6;
  font-weight: 600;
}

.status-finished {
  color: #94a3b8;
  font-weight: 600;
}

.status-disconnected {
  color: #ef4444;
  font-weight: 600;
  opacity: 0.6;
}

.status-none {
  color: #9ca3af;
}

/* Battery indicators */
.battery-low {
  color: #ef4444;
  font-weight: 600;
}

.battery-medium {
  color: #f59e0b;
  font-weight: 600;
}

/* Empty state */
.no-data {
  text-align: center;
  padding: 2rem 1rem;
  color: #9ca3af;
  font-style: italic;
  background-color: #111827;
  border-radius: 0.5rem;
}
</style>