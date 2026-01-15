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

  // ✅ NEW: available tables (optional for your UI)
  const availableTables = [
    'matches',
    'teams',
    'players',
    'results',
    'player_team_associations', // ← include new table
  ]

  async function fetchData() {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/data/${tableName.value}`)
      rows.value = res.data.map(row => {
        const { _sa_instance_state, ...cleaned } = row
        return cleaned
      })
    } catch (err) {
      console.error('Failed to fetch data:', err)
      rows.value = []
    }
  }

  function setTable(name) {
    tableName.value = name
    fetchData()
  }

  // 🔄 Update field in a row
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

  // 🧹 Delete a row
  async function deleteRow(id) {
    try {
      await axios.delete(`http://127.0.0.1:8000/data/${tableName.value}/${id}`)
      rows.value = rows.value.filter(r => r.id !== id)
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  // 🔍 Computed: search and sort
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

  // 📋 Fetch distinct player names
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

  // 📋 Fetch distinct team names
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

  // ✅ Optional: Fetch associations (players ↔ teams ↔ matches)
  async function fetchAssociations() {
    try {
      const res = await axios.get('http://127.0.0.1:8000/data/player_team_associations')
      return res.data.map(link => ({
        id: link.id,
        player_id: link.player_id,
        team_id: link.team_id,
        match_id: link.match_id,
        position: link.position,
      }))
    } catch (err) {
      console.error('Failed to fetch player–team associations', err)
      return []
    }
  }

  return {
    tableName,
    rows,
    searchQuery,
    sortKey,
    sortAsc,
    availableTables, // ✅ new
    setTable,
    fetchData,
    filteredRows,
    updateRow,
    deleteRow,
    playerNames,
    teamNames,
    fetchPlayerNames,
    fetchTeamNames,
    fetchAssociations, // ✅ new helper
  }
})
