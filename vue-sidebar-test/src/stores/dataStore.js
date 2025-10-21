// stores/dataStore.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useDataStore = defineStore('dataStore', () => {
  const tableName = ref('matches')
  const rows = ref([])
  const searchQuery = ref('')
  const sortKey = ref(null)
  const sortAsc = ref(true)
  const playerNames = ref([])
  const teamNames = ref([])

  async function fetchData() {
    const res = await axios.get(`http://127.0.0.1:8000/data/${tableName.value}`)
    rows.value = res.data.map(row => {
      const { _sa_instance_state, ...cleaned } = row
      return cleaned
    })
  }

  function setTable(name) {
    tableName.value = name
    fetchData()
  }

  // 🧠 New: Update a field
  async function updateRow(id, field, value) {
    const row = rows.value.find(r => r.id === id)
    if (!row) return
    row[field] = value // Optimistic update
    try {
      await axios.patch(`http://127.0.0.1:8000/data/${tableName.value}/${id}`, { [field]: value })
    } catch (err) {
      console.error('Update failed:', err)
      await fetchData() // revert if failed
    }
  }

  // 🧹 New: Delete a row
  async function deleteRow(id) {
    try {
      await axios.delete(`http://127.0.0.1:8000/data/${tableName.value}/${id}`)
      rows.value = rows.value.filter(r => r.id !== id)
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const filteredRows = computed(() => {
    let result = [...rows.value]
    if (searchQuery.value)
      result = result.filter(r =>
        JSON.stringify(r).toLowerCase().includes(searchQuery.value.toLowerCase())
      )
    if (sortKey.value)
      result.sort((a, b) => {
        const av = a[sortKey.value]
        const bv = b[sortKey.value]
        return sortAsc.value ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
      })
    return result
  })

  async function fetchPlayerNames() {
    try {
      const res = await axios.get('http://127.0.0.1:8000/data/players')
      playerNames.value = res.data
        .map(p => p.name)
        .filter(Boolean)
        .filter((v, i, a) => a.indexOf(v) === i)
        .sort()
    } catch (err) {
      console.error('Failed to fetch player names', err)
    }
  }

  async function fetchTeamNames() {
    try {
      const res = await axios.get('http://127.0.0.1:8000/data/teams')
      teamNames.value = res.data
        .map(t => t.name)
        .filter(Boolean)
        .filter((v, i, a) => a.indexOf(v) === i)
        .sort()
    } catch (err) {
      console.error('Failed to fetch team names', err)
    }
  }

  return {
    tableName,
    rows,
    searchQuery,
    sortKey,
    sortAsc,
    setTable,
    fetchData,
    filteredRows,
    updateRow,
    deleteRow,
    playerNames,
    teamNames,
    fetchPlayerNames,
    fetchTeamNames,
  }


})
