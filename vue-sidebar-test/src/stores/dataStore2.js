// stores/dataStore.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000/data'

export const useDataStore = defineStore('dataStore', () => {
    const tableName = ref('matches')
    const rows = ref([])
    const searchQuery = ref('')
    const sortKey = ref(null)
    const sortAsc = ref(true)
    const playerNames = ref([])
    const teamNames = ref([])

    async function fetchData() {
        try {
            const res = await axios.get(`${API_BASE}/${tableName.value}`)
            rows.value = res.data
        } catch (err) {
            console.error('Failed to fetch data:', err)
            rows.value = []
        }
    }

    async function setTable(name) {
        tableName.value = name
        await fetchData()
    }

    // 🧠 Update a single field in a row
    async function updateRow(id, field, value) {
        const row = rows.value.find(r => r.id === id)
        if (!row) return

        // Optimistic update
        const prevValue = row[field]
        row[field] = value

        try {
            await axios.patch(`${API_BASE}/${tableName.value}/${id}`, { [field]: value })
        } catch (err) {
            console.error('Update failed:', err)
            row[field] = prevValue
        }
    }

    // 🧹 Delete a row
    async function deleteRow(id) {
        try {
            await axios.delete(`${API_BASE}/${tableName.value}/${id}`)
            rows.value = rows.value.filter(r => r.id !== id)
        } catch (err) {
            console.error('Delete failed:', err)
        }
    }

    const filteredRows = computed(() => {
        let result = [...rows.value]

        if (searchQuery.value) {
            result = result.filter(r =>
                JSON.stringify(r).toLowerCase().includes(searchQuery.value.toLowerCase())
            )
        }

        if (sortKey.value) {
            result.sort((a, b) => {
                const av = a[sortKey.value]
                const bv = b[sortKey.value]
                if (av === bv) return 0
                return sortAsc.value ? (av > bv ? 1 : -1) : (av < bv ? 1 : -1)
            })
        }

        return result
    })

    async function fetchPlayerNames() {
        try {
            const res = await axios.get(`${API_BASE}/players`)
            playerNames.value = [...new Set(res.data.map(p => p.name).filter(Boolean))].sort()
        } catch (err) {
            console.error('Failed to fetch player names', err)
        }
    }

    async function fetchTeamNames() {
        try {
            const res = await axios.get(`${API_BASE}/teams`)
            teamNames.value = [...new Set(res.data.map(t => t.name).filter(Boolean))].sort()
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
        filteredRows,
        setTable,
        fetchData,
        updateRow,
        deleteRow,
        playerNames,
        teamNames,
        fetchPlayerNames,
        fetchTeamNames,
    }
})
