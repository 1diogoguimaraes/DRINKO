<template>
	<main id="Control-page" class="control-page">
		<div class="header">
			<h1 class="title">Control Panel</h1>
			<div class="header-actions">
				<button class="btn btn-create" @click="openCreateModal">
					＋ Create Match
				</button>
				<span class="separator"></span>
				<button class="btn btn-reset" @click="resetDevices">
					⟳ Reset All
				</button>
				<span class="separator"></span>
				<button class="btn btn-reset-matches" @click="resetMatches">🗑 Reset Matches</button>

			</div>
		</div>


		<div class="control-layout">


			<div class="matches-column">
				<h2 class="section-title">Matches</h2>
				<div class="card">
					<h2 class="card-title">Unassigned</h2>
					<ul>
						<li v-for="d in unassigned" :key="d.device_id">
							{{ d.device_id }} ({{ d.status }})
						</li>
					</ul>
				</div>

				<div class="card">
					<h2 class="card-title">Solo</h2>
					<div v-for="(devices, matchId) in soloByMatch" :key="matchId" class="match-section">
						<h3 class="match-header">
							<span>
								Match {{ matchId }}
								<span v-if="matchFinished(matchId)" class="winner-badge">🏁 Finished</span>
							</span>
							<div class="match-actions">
								<button class="btn btn-play" :disabled="!allLocked(devices)"
									@click="playMatch(matchId, 'solo')">▶ PLAY</button>
								<button class="btn btn-edit" @click="openEditModal(String(matchId))">✎ EDIT</button>
								<button class="btn" :class="matchFinished(matchId) ? 'btn-finalize' : 'btn-disabled'"
									:disabled="!matchFinished(matchId)" @click="finalizeMatch(matchId)">✔
									FINALIZE</button>
								<button class="btn btn-delete" @click="deleteMatch(matchId)">DELETE</button>
								<button class="btn btn-resend" @click="resendMatch(matchId)">RESEND</button>
							</div>
						</h3>

						<div class="table-container">
							<table class="data-table">
								<thead>
									<tr>
										<th class="table-header">Info</th>
										<th v-for="d in devices" :key="d.device_id" class="table-header">
											{{ d.player_name ?? 'Unnamed' }}<br />
											<span class="device-id">{{ d.device_id }}</span>
										</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="row in ['start_weight', 'end_weight', 'reaction_time_seconds', 'time_seconds', 'foul']"
										:key="row" class="table-row">
										<td class="table-label">{{ row.replace('_', ' ') }}</td>
										<td v-for="d in devices" :key="d.device_id + row" class="table-cell">
											<span v-if="row !== 'foul'">{{ d[row] ?? '-' }}</span>
											<span v-else>
												<span v-if="d.foul" class="foul-icon">⚠</span>
											</span>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					</div>
				</div>

				<div class="card">
					<h2 class="card-title">1v1</h2>
					<div v-for="(devices, matchId) in oneVsOneByMatch" :key="matchId" class="match-section">
						<h3 class="match-header">
							<span>Match {{ matchId }}</span>
							<div class="match-actions">
								<button class="btn btn-play" :disabled="!allLocked(devices)"
									@click="playMatch(matchId, '1v1')">▶ PLAY</button>
								<button class="btn btn-edit" @click="openEditModal(String(matchId))">✎ EDIT</button>
								<button class="btn btn-finalize" @click="finalizeMatch(matchId)">✔ FINALIZE</button>
								<button class="btn btn-delete" @click="deleteMatch(matchId)">DELETE</button>
								<button class="btn btn-resend" @click="resendMatch(matchId)">RESEND</button>
							</div>
						</h3>

						<div class="teams-grid">
							<div v-for="team in [0, 1]" :key="team" class="team-card">
								<h4 class="team-name">
									{{devices.find(d => d.team === team)?.team_name ?? `Team ${team}`}}
									<span v-if="isWinner(matchId, team)" class="winner-badge">🏆 WINNER</span>
								</h4>

								<table class="team-table">
									<thead>
										<tr>
											<th class="table-header">Info</th>
											<th v-for="d in devices.filter(x => x.team === team)" :key="d.device_id"
												class="table-header">
												{{ d.player_name ?? 'Unnamed' }}
												<div class="device-id">{{ d.device_id }}</div>
											</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="row in ['start_weight', 'end_weight', 'reaction_time_seconds', 'time_seconds', 'foul']"
											:key="row" class="table-row">
											<td class="table-label">{{ row.replace('_', ' ') }}</td>
											<td v-for="d in devices.filter(x => x.team === team)"
												:key="d.device_id + row" class="table-cell">
												<span v-if="row !== 'foul'">{{ d[row] ?? '-' }}</span>
												<span v-else>
													<svg v-if="d.foul" xmlns="http://www.w3.org/2000/svg"
														class="foul-svg" fill="none" viewBox="0 0 24 24"
														stroke="currentColor">
														<path stroke-linecap="round" stroke-linejoin="round"
															stroke-width="2"
															d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												</span>
											</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
				</div>

				<div class="card">
					<h2 class="card-title">Relay</h2>
					<div v-for="(devices, matchId) in relayByMatch" :key="matchId" class="match-section">
						<h3 class="match-header">
							<span>Match {{ matchId }}</span>
							<div class="match-actions">
								<button class="btn btn-play" :disabled="!allLocked(devices)"
									@click="playMatch(matchId, 'relay')">▶ PLAY</button>
								<button class="btn btn-edit" @click="openEditModal(String(matchId))">✎ EDIT</button>
								<button class="btn btn-finalize" @click="finalizeMatch(matchId)">✔ FINALIZE</button>
								<button class="btn btn-delete" @click="deleteMatch(matchId)">DELETE</button>
								<button class="btn btn-resend" @click="resendMatch(matchId)">RESEND</button>
							</div>
						</h3>

						<div class="teams-grid">
							<div v-for="team in [0, 1]" :key="team" class="team-card">
								<h4 class="team-name">
									{{devices.find(d => d.team === team)?.team_name ?? `Team ${team}`}}
									<span v-if="isWinner(matchId, team)" class="winner-badge">🏆 WINNER</span>
								</h4>

								<table class="team-table">
									<thead>
										<tr>
											<th class="table-header">Info</th>
											<th v-for="d in devices.filter(x => x.team === team)" :key="d.device_id"
												class="table-header">
												{{ d.player_name ?? 'Unnamed' }}
												<div class="device-id">{{ d.device_id }}</div>
											</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="row in ['start_weight', 'end_weight', 'reaction_time_seconds', 'time_seconds', 'foul']"
											:key="row" class="table-row">
											<td class="table-label">{{ row.replace('_', ' ') }}</td>
											<td v-for="d in devices.filter(x => x.team === team)"
												:key="d.device_id + row" class="table-cell">
												<span v-if="row !== 'foul'">{{ d[row] ?? '-' }}</span>
												<span v-else>
													<svg v-if="d.foul" xmlns="http://www.w3.org/2000/svg"
														class="foul-svg" fill="none" viewBox="0 0 24 24"
														stroke="currentColor">
														<path stroke-linecap="round" stroke-linejoin="round"
															stroke-width="2"
															d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												</span>
											</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
				</div>
				<div class="card">
					<h2 class="card-title">Solo Relay</h2>
					<div v-for="(devices, matchId) in soloRelayByMatch" :key="matchId" class="match-section">
						<h3 class="match-header">
							<span>Match {{ matchId }}</span>
							<div class="match-actions">
								<button class="btn btn-play" :disabled="!allLocked(devices)"
									@click="playMatch(matchId, 'relay')">▶ PLAY</button>
								<button class="btn btn-edit" @click="openEditModal(String(matchId))">✎ EDIT</button>
								<button class="btn btn-finalize" @click="finalizeMatch(matchId)">✔ FINALIZE</button>
								<button class="btn btn-delete" @click="deleteMatch(matchId)">DELETE</button>
								<button class="btn btn-resend" @click="resendMatch(matchId)">RESEND</button>
							</div>
						</h3>

						<div class="teams-grid">
							<div v-for="team in [0]" :key="team" class="team-card">
								<h4 class="team-name">
									{{devices.find(d => d.team === team)?.team_name ?? `Team ${team}`}}
									<span v-if="isWinner(matchId, team)" class="winner-badge">🏆 WINNER</span>
								</h4>

								<table class="team-table">
									<thead>
										<tr>
											<th class="table-header">Info</th>
											<th v-for="d in devices.filter(x => x.team === team)" :key="d.device_id"
												class="table-header">
												{{ d.player_name ?? 'Unnamed' }}
												<div class="device-id">{{ d.device_id }}</div>
											</th>
										</tr>
									</thead>
									<tbody>
										<tr v-for="row in ['start_weight', 'end_weight', 'reaction_time_seconds', 'time_seconds', 'foul']"
											:key="row" class="table-row">
											<td class="table-label">{{ row.replace('_', ' ') }}</td>
											<td v-for="d in devices.filter(x => x.team === team)"
												:key="d.device_id + row" class="table-cell">
												<span v-if="row !== 'foul'">{{ d[row] ?? '-' }}</span>
												<span v-else>
													<svg v-if="d.foul" xmlns="http://www.w3.org/2000/svg"
														class="foul-svg" fill="none" viewBox="0 0 24 24"
														stroke="currentColor">
														<path stroke-linecap="round" stroke-linejoin="round"
															stroke-width="2"
															d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												</span>
											</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="status-column">
				<h2 class="section-title">📊 Live Device Status</h2>
				<StandartTable :data="statusArray" />
			</div>
		</div>
		<div v-if="showCreateModal" class="modal">
			<div class="modal-content">
				<h2 class="modal-title">Create Match</h2>

				<label class="input-label">Mode:</label>
				<select v-model="newMatchType" class="select-input">
					<option value="solo">Solo</option>
					<option value="1v1">1v1</option>
					<option value="relay">Relay</option>
					<option value="solo_relay">Solo Relay</option>
				</select>

				<div class="f1-delay-toggle">
					<input type="checkbox" id="f1_delay" v-model="useF1Delay" class="checkbox-input" />
					<label for="f1_delay" class="checkbox-label">Enable F1 Style Random Delay</label>
				</div>

				<div v-if="newMatchType === 'solo'" class="device-selection">
					<label class="input-label">Select Device:</label>
					<div class="device-grid">
						<button v-for="d in unassigned" :key="d.device_id" @click="toggleDevice(d.device_id)"
							:disabled="isDisabled(d.device_id)"
							:class="['device-btn', selectedDevices.includes(d.device_id) ? 'device-btn-selected' : '', isDisabled(d.device_id) ? 'device-btn-disabled' : '']">
							<span class="device-indicator"
								:class="selectedDevices.includes(d.device_id) ? 'indicator-active' : ''"></span>
							<span class="device-id-text">{{ d.device_id }}</span>
							<span v-if="selectedDevices.includes(d.device_id)" class="check-mark">✔</span>
						</button>
					</div>
				</div>

				<div v-else-if="newMatchType === '1v1'" class="teams-selection">
					<div>
						<h3 class="team-header team-a">Team A</h3>
						<div class="device-grid-center">
							<button v-for="d in unassigned" :key="'A-' + d.device_id"
								@click="assignToTeam(d.device_id, 0)" :disabled="isTeamDevice(d.device_id, 1)"
								:class="teamButtonClass(d.device_id, 0)">
								{{ d.device_id }}
							</button>
						</div>
					</div>
					<div>
						<h3 class="team-header team-b">Team B</h3>
						<div class="device-grid-center">
							<button v-for="d in unassigned" :key="'B-' + d.device_id"
								@click="assignToTeam(d.device_id, 1)" :disabled="isTeamDevice(d.device_id, 0)"
								:class="teamButtonClass(d.device_id, 1)">
								{{ d.device_id }}
							</button>
						</div>
					</div>
				</div>

				<div v-else-if="newMatchType === 'relay'" class="teams-selection">
					<div>
						<h3 class="team-header team-a">Team A</h3>
						<div class="device-grid-center">
							<button v-for="d in unassigned" :key="'RA-' + d.device_id"
								@click="assignToTeam(d.device_id, 0)" :disabled="isTeamDevice(d.device_id, 1)"
								:class="teamButtonClass(d.device_id, 0)">
								{{ d.device_id }}
							</button>
						</div>
					</div>
					<div>
						<h3 class="team-header team-b">Team B</h3>
						<div class="device-grid-center">
							<button v-for="d in unassigned" :key="'RB-' + d.device_id"
								@click="assignToTeam(d.device_id, 1)" :disabled="isTeamDevice(d.device_id, 0)"
								:class="teamButtonClass(d.device_id, 1)">
								{{ d.device_id }}
							</button>
						</div>
					</div>
				</div>
				<div v-else-if="newMatchType === 'solo_relay'" class="teams-selection">
					<div>
						<h3 class="team-header team-a">Team</h3>
						<div class="device-grid-center">
							<button v-for="d in unassigned" :key="'SR-' + d.device_id"
								@click="assignToTeam(d.device_id, 0)" :class="teamButtonClass(d.device_id, 0)">
								{{ d.device_id }}
							</button>
						</div>
					</div>
				</div>


				<p v-if="validationError" class="error-message">{{ validationError }}</p>

				<div class="modal-actions">
					<button class="btn btn-cancel" @click="closeCreateModal">Cancel</button>
					<span class="separator">|</span>
					<button class="btn btn-confirm" @click="createMatch">Create</button>
				</div>
			</div>
		</div>

		<div v-if="showEditModal && editingMatch && editingMatch.teams" class="modal">
			<div class="modal-content">
				<h2 class="modal-title">Edit Match {{ editingMatchId }}</h2>

				<div v-for="(team, tIndex) in editingMatch.teams" :key="tIndex" class="edit-team">
					<label class="input-label">Team {{ tIndex }} Name:</label>
					<AutoCompleteInput v-model="team.team_name" :suggestions="dataStore.teamNames"
						placeholder="Enter or select team name" />

					<div v-for="(player, pIndex) in team.players ?? []" :key="player.device_id" class="edit-player">
						<label class="input-label-small">Player ({{ player.device_id }}):</label>
						<AutoCompleteInput v-model="player.player_name" :suggestions="dataStore.playerNames"
							placeholder="Enter or select player name" />
					</div>
				</div>

				<div class="modal-actions">
					<button class="btn btn-cancel" @click="closeEditModal">Cancel</button>
					<span class="separator">|</span>
					<button class="btn btn-confirm" @click="saveEditMatch">Save</button>
				</div>
			</div>
		</div>


	</main>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useDataStore } from '../stores/dataStore'
import AutoCompleteInput from '../components/AutoCompleteInput.vue'
import StandartTable from '../components/StandartTable.vue' // ✅ imported table




const statuses = reactive({}) // device_id → status info
const players = ref({}) // device_id → player info
const matchesMemory = ref({}) // match_id → full match snapshot

let socketDevices = null
let socketPlayers = null

const dataStore = useDataStore()


onMounted(() => {

	dataStore.fetchPlayerNames()
	dataStore.fetchTeamNames()

	// --- Devices WebSocket ---
	socketDevices = new WebSocket('ws://localhost:8000/ws/live')
	socketDevices.onmessage = (event) => {
		const data = JSON.parse(event.data)

		// 🔹 Snapshot of all devices
		if (data.type === 'devices_snapshot') {
			for (const [device_id, info] of Object.entries(data.devices)) {
				statuses[device_id] = {
					device_id,
					status: info.status ?? 'unknown',
					match: info.match_id ?? null,
					mode: info.mode ?? null,
					team: info.team != null ? Number(info.team) : null,
					relay_pos: info.relay_pos ?? null,
					battery: info.battery ?? null,
				}
			}
		}

		// 🔹 Device status updates
		else if (data.type === 'status') {
			if (data.status === 'disconnected') {
				// 🧹 completely remove and skip reassign
				delete statuses[data.device_id]
				return
			}

			// otherwise, update or create entry
			statuses[data.device_id] = {
				device_id: data.device_id,
				status: data.status,
				match: data.match_id ?? null,
				mode: data.mode ?? null,
				team: data.team != null ? Number(data.team) : null,
				relay_pos: data.relay_pos ?? null,
				battery: data.battery ?? null,
			}

			// force Vue reactivity
			statuses[data.device_id] = { ...statuses[data.device_id] }
		}


		// 🔹 Optional: handle weight updates from live events
		else if (data.type === 'weight') {
			if (!statuses[data.device_id]) statuses[data.device_id] = { device_id: data.device_id }
			statuses[data.device_id].start_weight = data.start_weight
		}
	}


	socketPlayers = new WebSocket('ws://localhost:8000/ws/matches')

	socketPlayers.onmessage = (event) => {
		const data = JSON.parse(event.data)
		console.log(data)
		if (data.type === 'matches_snapshot' || data.type === 'matches_update') {
			const incoming = data.data ?? {}

			// Replace the object safely
			matchesMemory.value = { ...matchesMemory.value, ...incoming }

			// Update players map
			let updatedPlayers = { ...players.value }

			for (const [matchId, match] of Object.entries(incoming)) {
				if (Array.isArray(match.teams)) {
					for (const team of match.teams) {
						for (const player of team.players ?? []) {
							updatedPlayers[player.device_id] = {
								player_name: player.player_name ?? null,
								team_name: team.team_name ?? null,
								start_weight: player.start_weight ?? null,
								end_weight: player.end_weight ?? null,
								reaction_time_seconds: player.reaction_time_seconds ?? null,
								time_seconds: player.time_seconds ?? null,
								foul: player.foul ?? false
							}
						}
					}
				}
			}

			players.value = updatedPlayers
		}

	}





})

onBeforeUnmount(() => {
	if (socketDevices) socketDevices.close()
	if (socketPlayers) socketPlayers.close()
})




// merge device + player info
function mergeDevice(d) {
	return { ...d, ...(players.value[d.device_id] || {}) } // FIXED: players.value
}

// categories with merged data
const unassigned = computed(() =>
	Object.values(statuses)
		.filter((d) => !d.mode && d.status !== 'disconnected')
		.map(mergeDevice)
)

const solo = computed(() =>
	Object.values(statuses)
		.filter((d) => d.mode === 'solo' && d.status !== 'disconnected')
		.map(mergeDevice)
)

const oneVsOne = computed(() =>
	Object.values(statuses)
		.filter((d) => d.mode === '1v1' && d.status !== 'disconnected')
		.map(mergeDevice)
)

const relay = computed(() =>
	Object.values(statuses)
		.filter((d) => d.mode === 'relay' && d.status !== 'disconnected')
		.map(mergeDevice)
)

// computed array for StandartTable
const statusArray = computed(() => Object.values(statuses))


// group by match_id
function groupByMatch(devices) {
	return devices.reduce((acc, d) => {
		const matchId = d.match ?? 'unassigned'
		if (!acc[matchId]) acc[matchId] = []
		acc[matchId].push(d)
		return acc
	}, {})
}

function makeTeamRows(devices) {
	const team0 = devices.filter((r) => r.team === 0).sort((a, b) => a.relay_pos - b.relay_pos)
	const team1 = devices.filter((r) => r.team === 1).sort((a, b) => a.relay_pos - b.relay_pos)

	const maxLen = Math.max(team0.length, team1.length)
	const rows = []
	for (let i = 0; i < maxLen; i++) {
		rows.push([team0[i] || null, team1[i] || null])
	}
	return rows
}




// --- Solo matches from matchesMemory ---
const soloByMatch = computed(() => {
	const result = {}
	for (const [matchId, match] of Object.entries(matchesMemory.value)) {
		if (match.match_type === "solo") {
			const players = []
			match.teams.forEach((team, teamIndex) => {
				team.players.forEach((p) => {
					players.push({
						...p,
						team: teamIndex,
						team_name: team.team_name
					})
				})
			})
			result[matchId] = players
		}
	}
	return result
})

// --- 1v1 matches ---
const oneVsOneByMatch = computed(() => {
	const result = {}
	for (const [matchId, match] of Object.entries(matchesMemory.value)) {
		if (match.match_type === "1v1") {
			const players = []
			match.teams.forEach((team, teamIndex) => {
				const teamName = team.team_name ?? `Team ${teamIndex}`
				team.players.forEach((p) => {
					players.push({
						...p,
						team: teamIndex,
						team_name: teamName,
						relay_pos: p.relay_pos ?? 0
					})
				})
			})
			result[matchId] = players
		}
	}
	return result
})

// --- Relay matches ---
const relayByMatch = computed(() => {
	const result = {}
	for (const [matchId, match] of Object.entries(matchesMemory.value)) {
		if (match.match_type === "relay") {
			const players = []
			match.teams.forEach((team, teamIndex) => {
				const teamName = team.team_name ?? `Team ${teamIndex}`
				team.players.forEach((p) => {
					players.push({
						...p,
						team: teamIndex,
						team_name: teamName,
						relay_pos: p.relay_pos ?? 0
					})
				})
			})
			result[matchId] = players
		}
	}
	return result
})

const soloRelayByMatch = computed(() => {
	const result = {}
	for (const [matchId, match] of Object.entries(matchesMemory.value)) {
		if (match.match_type === "solo_relay") {
			const players = []
			match.teams.forEach((team, teamIndex) => {
				const teamName = team.team_name ?? `Team ${teamIndex}`
				team.players.forEach((p) => {
					players.push({
						...p,
						team: teamIndex,
						team_name: teamName,
						relay_pos: p.relay_pos ?? 0
					})
				})
			})
			result[matchId] = players
		}
	}
	return result
})

function allLocked(devices) {
	return devices.length > 0 && devices.every((d) => statuses[d.device_id]?.status === 'locked') // FIXED: Check actual status
}
function matchFinished(matchId) {
	const match = matchesMemory.value[String(matchId)]
	if (!match) return false
	return match.status === 'finished' || match.finished === true
}

function isWinner(matchId, teamIndex) {
	const match = matchesMemory.value[String(matchId)]
	if (!match || match.status !== 'finished') return false
	return match.winner_team === teamIndex
}
async function playMatch(matchId, mode) {
	try {
		const res = await fetch(`http://localhost:8000/matches/${matchId}/start`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ mode })
		})
		if (!res.ok) throw new Error(`Failed to start match ${matchId}`)
		console.log(`✅ Match ${matchId} (${mode}) started`)
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}

async function resetDevices() {
	try {
		const res = await fetch('http://localhost:8000/devices/reset', {
			method: 'POST'
		})
		if (!res.ok) throw new Error('Failed to reset devices')
		console.log('✅ Reset signal sent to all devices')
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}
// Reset all matches
async function resetMatches() {
	if (!confirm("Are you sure you want to reset all matches? This cannot be undone.")) return
	try {
		const res = await fetch('http://localhost:8000/matches/reset', {
			method: 'POST'
		})
		if (!res.ok) throw new Error('Failed to reset matches')
		console.log('✅ All matches reset')
		// Clear local memory
		matchesMemory.value = {}
		alert('All matches have been reset!')
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}

async function deleteMatch(matchId) {
	if (!confirm(`Delete match ${matchId}? This cannot be undone.`)) return
	try {
		const res = await fetch(`http://localhost:8000/matches/${matchId}`, {
			method: 'DELETE'
		})
		if (!res.ok) throw new Error('Failed to delete match')
		console.log(`✅ Match ${matchId} deleted`)
		delete matchesMemory.value[matchId]
		alert(`Match ${matchId} has been deleted!`)
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}

async function resendMatch(matchId) {
	try {
		const res = await fetch(`http://localhost:8000/matches/${matchId}/resend`, {
			method: 'POST'
		})
		if (!res.ok) throw new Error('Failed to resend match data')
		console.log(`✅ Match ${matchId} data resent`)
		alert(`Match ${matchId} data has been resent to devices!`)
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}



// Modal state
const showCreateModal = ref(false)
const newMatchType = ref('solo')
const selectedDevices = ref([])
const useF1Delay = ref(false) // ✅ NEW: F1 Delay State

function openCreateModal() {
	showCreateModal.value = true
	selectedDevices.value = []
	newMatchType.value = 'solo'
	teamAssignments.value = { 0: [], 1: [] } // reset
	useF1Delay.value = false // reset
}
function closeCreateModal() {
	showCreateModal.value = false
	selectedDevices.value = []
	teamAssignments.value = { 0: [], 1: [] } // reset
	useF1Delay.value = false
}


// toggle device in selection
function toggleDevice(deviceId) {
	if (selectedDevices.value.includes(deviceId)) {
		selectedDevices.value = selectedDevices.value.filter((id) => id !== deviceId)
	} else {
		selectedDevices.value.push(deviceId)
	}
}

// Build player object
function buildPlayer(deviceId) {
	return {
		device_id: deviceId,
		status: 'none',
		player_name: null,
		time_seconds: null,
		reaction_time_seconds: null,
		start_weight: null,
		end_weight: null,
		foul: false
	}
}


const validationError = ref(null)

// Disable devices if already at limit for mode
function isDisabled(deviceId) {
	if (newMatchType.value === 'solo') {
		return selectedDevices.value.length >= 1 && !selectedDevices.value.includes(deviceId)
	}
	if (newMatchType.value === '1v1') {
		return selectedDevices.value.length >= 2 && !selectedDevices.value.includes(deviceId)
	}
	if (newMatchType.value === 'relay') {
		// max 10 (5 per team)
		return selectedDevices.value.length >= 10 && !selectedDevices.value.includes(deviceId)
	}
	if (newMatchType.value === 'solo_relay') {
		// max 5 (5 per team)
		return selectedDevices.value.length >= 5 && !selectedDevices.value.includes(deviceId)
	}
	return false
}

// Enforce rules on create
async function createMatch() {
	validationError.value = null

	// --- Gather chosen devices ---
	let devices =
		newMatchType.value === 'solo'
			? selectedDevices.value
			: [...teamAssignments.value[0], ...teamAssignments.value[1]]

	// --- Validate depending on mode ---
	if (newMatchType.value === 'solo' && devices.length !== 1) {
		validationError.value = 'Solo match requires exactly 1 device.'
		return
	}
	if (newMatchType.value === '1v1') {
		if (teamAssignments.value[0].length !== 1 || teamAssignments.value[1].length !== 1) {
			validationError.value = '1v1 match requires exactly 1 device per team.'
			return
		}
	}
	if (newMatchType.value === 'relay') {
		const a = teamAssignments.value[0].length
		const b = teamAssignments.value[1].length
		if (!((a === 2 && b === 2) || (a === 3 && b === 3) || (a === 4 && b === 4) || (a === 5 && b === 5))) {
			validationError.value = 'Relay must have 2,3,4 or 5 devices per team.'
			return
		}
	}
	if (newMatchType.value === 'solo_relay') {
		const a = teamAssignments.value[0].length
		if (!((a === 2 || a === 3 || a === 4 || a === 5))) {
			validationError.value = 'Solo Relay must have 2,3,4 or 5 devices.'
			return
		}
	}

	// --- Build payload & send ---
	try {
		const payload = buildMatchPayload(newMatchType.value, devices)
		console.log(payload)
		const res = await fetch('http://localhost:8000/matches/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		})
		if (!res.ok) throw new Error('Failed to create match')
		console.log('✅ Match created', payload)
		closeCreateModal()
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}


// Build JSON payload (small tweak for relay validation)
function buildMatchPayload(type, devices) {
	if (type === 'solo') {
		return {
			match_type: 'solo',
			f1_delay: useF1Delay.value, // ✅ NEW
			teams: [
				{
					team_name: null,
					finished: false,
					players: [buildPlayer(devices[0])]
				}
			]
		}
	}

	if (type === '1v1') {
		return {
			match_type: '1v1',
			f1_delay: useF1Delay.value, // ✅ NEW
			teams: [
				{ team_name: null, finished: false, players: [buildPlayer(devices[0])] },
				{ team_name: null, finished: false, players: [buildPlayer(devices[1])] }
			]
		}
	}

	if (type === 'relay') {
		const half = devices.length / 2 // safe because already validated
		return {
			match_type: 'relay',
			f1_delay: useF1Delay.value, // ✅ NEW
			teams: [
				{ team_name: null, finished: false, players: devices.slice(0, half).map(buildPlayer) },
				{ team_name: null, finished: false, players: devices.slice(half).map(buildPlayer) }
			]
		}
	}
	if (type === 'solo_relay') {
		return {
			match_type: 'solo_relay',
			f1_delay: useF1Delay.value, // ✅ NEW
			teams: [
				{
					team_name: null,
					finished: false,
					players: devices.map((deviceId, index) => ({
						...buildPlayer(deviceId),
						relay_pos: index // assign relay order
					}))
				}
			]
		}
	}

}

// --- Edit Modal State ---
const showEditModal = ref(false)
const editingMatchId = ref(null)
const editingMatch = ref(null) // store full match object for editing

function openEditModal(matchId) {
	const match = matchesMemory.value[String(matchId)]
	if (!match) {
		alert("Match not found in memory")
		return
	}
	editingMatchId.value = String(matchId)
	editingMatch.value = JSON.parse(JSON.stringify(match))
	showEditModal.value = true
}



function closeEditModal() {
	showEditModal.value = false
	editingMatchId.value = null
	editingMatch.value = null
}

async function saveEditMatch() {
	try {
		const payload = editingMatch.value
		const res = await fetch(`http://localhost:8000/matches/${editingMatchId.value}/update`, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		})
		if (!res.ok) throw new Error('Failed to update match')
		console.log('✅ Match updated', payload)
		closeEditModal()
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}
async function finalizeMatch(matchId) {
	try {
		const res = await fetch(`http://localhost:8000/matches/${matchId}/finalize`, {
			method: "POST"
		})
		if (!res.ok) throw new Error(`Failed to finalize match ${matchId}`)

		const data = await res.json()
		console.log("✅ Match finalized", data)

		// Optimistic update: remove from matchesMemory
		const newMem = { ...matchesMemory.value }
		delete newMem[matchId]
		matchesMemory.value = newMem

		alert(`Match ${matchId} finalized and saved!`)
	} catch (err) {
		console.error(err)
		alert(`Error: ${err.message}`)
	}
}

// --- New team assignment logic for 1v1 & relay ---
const teamAssignments = ref({
	0: [], // Team A
	1: [], // Team B
})

function assignToTeam(deviceId, team) {
	// If already in this team → remove
	if (teamAssignments.value[team].includes(deviceId)) {
		teamAssignments.value[team] = teamAssignments.value[team].filter((id) => id !== deviceId)
		return
	}

	// Remove from other team if needed
	const otherTeam = team === 0 ? 1 : 0
	teamAssignments.value[otherTeam] = teamAssignments.value[otherTeam].filter((id) => id !== deviceId)

	// Limit counts depending on mode
	if (newMatchType.value === '1v1' && teamAssignments.value[team].length >= 1) return
	if (newMatchType.value === 'relay' && teamAssignments.value[team].length >= 5) return

	teamAssignments.value[team].push(deviceId)
}

function isTeamDevice(deviceId, team) {
	return teamAssignments.value[team].includes(deviceId)
}

function teamButtonClass(deviceId, team) {
	const isSelected = teamAssignments.value[team].includes(deviceId)
	const disabled = isTeamDevice(deviceId, team === 0 ? 1 : 0)

	let classes = ['team-btn']

	if (isSelected) {
		classes.push(team === 0 ? 'team-btn-a-selected' : 'team-btn-b-selected')
	}

	if (disabled) {
		classes.push('team-btn-disabled')
	}

	return classes.join(' ')
}


</script>

<style scoped>
/* Main container */
.control-page {
	padding: 1rem;
}

/* Header */
.header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 1rem;
}

.title {
	font-size: 1.5rem;
	font-weight: bold;
}

.header-actions {
	display: flex;
	gap: 0.5rem;
	align-items: center;
}

.separator {
	margin: 0 0.25rem;
}

/* Buttons */
.btn {
	padding: 0.5rem 1rem;
	border-radius: 0.375rem;
	border: none;
	cursor: pointer;
	font-weight: 500;
	transition: all 0.2s;
}

.btn-create {
	background-color: #16a34a;
	color: white;
}

.btn-create:hover {
	background-color: #15803d;
}

.btn-reset {
	background-color: #dc2626;
	color: white;
}

.btn-reset:hover {
	background-color: #b91c1c;
}

.btn-reset-matches {
	background-color: #dc2626;
	color: white;
}

.btn-reset-matches:hover {
	background-color: #b91c1c;

}

.btn-play {
	background-color: #3b82f6;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
}

.btn-play:disabled {
	background-color: #6b7280;
	cursor: not-allowed;
}

.btn-edit {
	background-color: #eab308;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
}

.btn-edit:hover {
	background-color: #bc8f06;
}

.btn-finalize {
	background-color: #dc2626;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
}

.btn-finalize:hover {
	background-color: #b91c1c;
}


.btn-delete {
	background-color: #dc2626;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
}

.btn-delete:hover {
	background-color: #b91c1c;
}

.btn-resend {
	background-color: #3b82f6;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
}

.btn-resend:hover {
	background-color: #2b5eb0;
}

.btn-disabled {
	background-color: #6b7280;
	color: white;
	padding: 0.25rem 0.75rem;
	font-size: 0.875rem;
	cursor: not-allowed;
}

.btn-cancel {
	background-color: #6b7280;
	color: white;
}

.btn-confirm {
	background-color: #3b82f6;
	color: white;
}

/* Layout */
.control-layout {
	display: grid;
	grid-template-columns: 1fr;
	gap: 1.5rem;
	height: calc(100vh - 6rem);
}

@media (min-width: 1024px) {
	.control-layout {
		grid-template-columns: 1.5fr 1.5fr;
	}
}

.matches-column {
	display: flex;
	flex-direction: column;
	gap: 1.5rem;
	overflow-y: auto;
	height: 100%;
	padding: 1rem;
	border: 1px solid #ddd;
	border-radius: 0.5rem;
	background: #fff;
	box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
	min-width: 0;
}

.status-column {
	border: 1px solid #ddd;
	border-radius: 0.5rem;
	padding: 1rem;
	background: #fff;
	box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
	/*overflow-y: auto;*/
	height: 100%;
}

/* Section titles */
.section-title {
	font-weight: 600;
	margin-bottom: 0.75rem;
	font-size: 1.125rem;
	color: #374151;
}

/* Cards */
.card {
	border: 1px solid #e5e7eb;
	border-radius: 0.5rem;
	padding: 0.75rem;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-title {
	font-weight: 600;
	margin-bottom: 0.5rem;
}

/* Match sections */
.match-section {
	margin-bottom: 1.5rem;
}

.match-header {
	font-weight: 500;
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 0.5rem;
}

.match-actions {
	display: flex;
	gap: 0.25rem;
}

/* Tables */
.table-container {
	overflow-x: auto;
}

.data-table {
	width: 100%;
	border-collapse: collapse;
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

.table-header {
	padding: 0.5rem;
	border-right: 1px solid #374151;
}

.table-row {
	transition: background-color 0.2s;
}

.table-row:hover {
	background-color: #1f2937;
}

.table-label {
	font-weight: 600;
	text-transform: capitalize;
	padding: 0.5rem;
	border-top: 1px solid #374151;
}

.table-cell {
	padding: 0.5rem;
	border-top: 1px solid #374151;
}

.device-id {
	font-size: 0.75rem;
	color: #9ca3af;
}

.foul-icon {
	color: #fbbf24;
	font-size: 1.25rem;
}

.foul-svg {
	width: 1.25rem;
	height: 1.25rem;
	color: white;
	display: inline-block;
}

/* Team grids */
.teams-grid {
	display: grid;
	grid-template-columns: 1fr;
	gap: 1rem;
}

@media (min-width: 768px) {
	.teams-grid {
		grid-template-columns: 1fr 1fr;
	}
}

.team-card {
	background-color: #111827;
	border-radius: 0.5rem;
	padding: 0.5rem;
}

.team-name {
	text-align: center;
	font-size: 0.875rem;
	font-weight: bold;
	color: #e5e7eb;
	margin-bottom: 0.5rem;
}

.team-table {
	width: 100%;
	font-size: 0.875rem;
	text-align: center;
	border-collapse: collapse;
	background-color: #111827;
	color: #f3f4f6;
}

.team-table thead {
	background-color: #1f2937;
	color: #d1d5db;
}


/* Modal */
.modal {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.7);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 1000;
}

.modal-content {
	background: #f9fafb;
	padding: 1.5rem;
	border-radius: 0.75rem;
	width: 420px;
	max-width: 90vw;
	box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
	max-height: 90vh;
	overflow-y: auto;
}

.modal-title {
	font-size: 1.125rem;
	font-weight: bold;
	margin-bottom: 0.75rem;
}

.input-label {
	display: block;
	margin-bottom: 0.5rem;
	font-weight: 500;
}

.input-label-small {
	display: block;
	font-weight: 400;
	font-size: 0.875rem;
}

.select-input {
	width: 100%;
	padding: 0.5rem;
	margin-bottom: 1rem;
	border-radius: 0.375rem;
	background-color: #1f2937;
	color: white;
	border: 1px solid #374151;
}

/* F1 Delay Toggle Styling */
.f1-delay-toggle {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	margin-bottom: 1rem;
	padding: 0.5rem;
	background-color: #e5e7eb;
	border-radius: 0.375rem;
	border: 1px solid #d1d5db;
}

.checkbox-input {
	width: 1.25rem;
	height: 1.25rem;
	cursor: pointer;
}

.checkbox-label {
	font-weight: 500;
	color: #1f2937;
	cursor: pointer;
}

/* Device selection */
.device-selection {
	margin-top: 0.5rem;
}

.device-grid {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
}

.device-btn {
	padding: 0.5rem 1rem;
	border-radius: 0.75rem;
	border: 1px solid #d1d5db;
	font-weight: 500;
	transition: all 0.2s;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	display: flex;
	align-items: center;
	gap: 0.5rem;
	background-color: #f3f4f6;
	color: #1f2937;
	cursor: pointer;
}

.device-btn:hover {
	background-color: #e5e7eb;
}

.device-btn-selected {
	background-color: #3b82f6;
	color: white;
	border-color: #3b82f6;
	transform: scale(1.05);
}

.device-btn-disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

.device-indicator {
	width: 0.625rem;
	height: 0.625rem;
	border-radius: 50%;
	background-color: #9ca3af;
}

.indicator-active {
	background-color: white;
}

.device-id-text {
	font-family: monospace;
	font-size: 0.875rem;
}

.check-mark {
	color: white;
	font-size: 0.75rem;
	font-weight: 600;
}

/* Teams selection */
.teams-selection {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 1rem;
	margin-top: 0.5rem;
}

.team-header {
	text-align: center;
	font-weight: 600;
	margin-bottom: 0.5rem;
}

.team-a {
	color: #3b82f6;
}

.team-b {
	color: #dc2626;
}

.device-grid-center {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
	justify-content: center;
}

/* Team buttons */
.team-btn {
	padding: 0.5rem 1rem;
	border-radius: 0.75rem;
	border: 1px solid #d1d5db;
	font-weight: 500;
	transition: all 0.2s;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
	background-color: #f3f4f6;
	color: #1f2937;
	cursor: pointer;
}

.team-btn:hover {
	background-color: #e5e7eb;
}

.team-btn-a-selected {
	background-color: #3b82f6;
	color: white;
	border-color: #3b82f6;
	transform: scale(1.05);
}

.team-btn-b-selected {
	background-color: #dc2626;
	color: white;
	border-color: #dc2626;
	transform: scale(1.05);
}

.team-btn-disabled {
	opacity: 0.5;
	cursor: not-allowed;
}

/* Error message */
.error-message {
	color: #dc2626;
	margin-top: 0.75rem;
	font-size: 0.875rem;
}

/* Modal actions */
.modal-actions {
	display: flex;
	justify-content: flex-end;
	gap: 0.5rem;
	margin-top: 1.5rem;
	align-items: center;
}

/* Edit forms */
.edit-team {
	margin-bottom: 1rem;
}

.edit-player {
	margin-left: 1rem;
	margin-bottom: 0.5rem;
}

.winner-badge {
	background-color: #fbbf24;
	color: #92400e;
	padding: 0.1rem 0.5rem;
	border-radius: 1rem;
	font-size: 0.75rem;
	margin-left: 0.5rem;
	vertical-align: middle;
	font-weight: bold;
}
</style>