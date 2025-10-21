<template>
  <div class="page-container">
    <div class="table-wrapper">
      <!-- Filters -->
      <div class="controls">
        <select v-model="store.tableName" @change="store.setTable(store.tableName)">
          <option value="matches">Matches</option>
          <option value="teams">Teams</option>
          <option value="players">Players</option>
          <option value="results">Results</option>
        </select>
        <input v-model="store.searchQuery" placeholder="Search..." />
      </div>

      <!-- Scrollable Table -->
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th v-for="key in tableKeys" :key="key" @click="sortBy(key)">
                {{ key }}
                <span v-if="store.sortKey === key">{{ store.sortAsc ? "▲" : "▼" }}</span>
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in store.filteredRows" :key="i">
              <td v-for="key in tableKeys" :key="key" @dblclick="startEdit(row.id, key, row[key])">
                <template v-if="isEditing(row.id, key)">
                  <input v-model="editValue" @keyup.enter="saveEdit(row.id, key)" @blur="saveEdit(row.id, key)"
                    class="border px-1 py-0.5 w-full" autofocus />
                </template>
                <template v-else>
                  {{ row[key] }}
                </template>
              </td>
              <td>
                <button @click="store.deleteRow(row.id)" class="text-red-600 hover:underline">
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDataStore } from '@/stores/dataStore'

const store = useDataStore()
const tableKeys = computed(() => (store.rows.length ? Object.keys(store.rows[0]) : []))

const editing = ref({ id: null, field: null })
const editValue = ref('')

function isEditing(id, field) {
  return editing.value.id === id && editing.value.field === field
}

function startEdit(id, field, value) {
  editing.value = { id, field }
  editValue.value = value
}

async function saveEdit(id, field) {
  await store.updateRow(id, field, editValue.value)
  editing.value = { id: null, field: null }
}

function sortBy(key) {
  if (store.sortKey === key) store.sortAsc = !store.sortAsc
  else {
    store.sortKey = key
    store.sortAsc = true
  }
}

onMounted(() => store.fetchData())
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  background-color: #f3f4f6;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.table-wrapper {
  width: 90%;
  max-width: 1200px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.controls select,
.controls input {
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 6px 8px;
  flex: 1;
}

.table-container {
  height: 500px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
}

table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  text-align: left;
}

th,
td {
  padding: 10px;
  border-bottom: 1px solid #e0e0e0;
  word-wrap: break-word;
  white-space: normal;
}

thead th {
  position: sticky;
  top: 0;
  background-color: #f9fafb;
  z-index: 2;
}

tbody tr:hover {
  background-color: #f5f5f5;
}
</style>
