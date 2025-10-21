<!-- PublicView.vue-->
<template>
    <main id="Public-page">
        <div class="logo">
            <img :src="logoURL" alt="FINOS" class="responsive-logo" />
        </div>
        <div>
            <button v-if="$route.meta.hideNav" @click="homebut">Home</button>
        </div>

        <!-- 🧩 Main content split -->
        <div class="content-wrapper">
            <!-- LEFT: Leaderboard -->
            <div class="scoreboard">
                <div class="header">
                    <button class="arrow-btn" @click="prevView">⟵</button>
                    <div class="titles">
                        <h1>{{ currentViewTitle }}</h1>
                        <p>{{ currentViewSubtitle }}</p>
                    </div>
                    <button class="arrow-btn" @click="nextView">⟶</button>
                </div>

                <div class="auto-switch-toggle">
                    <button @click="toggleAutoSwitch">
                        🔁 Auto Switch: {{ isAutoSwitching ? 'ON' : 'OFF' }}
                    </button>
                </div>

                <table id="PositionsTable">
                    <thead>
                        <tr>
                            <th>Position</th>
                            <th>Name</th>
                            <th v-if="currentView === 'best'">Match</th>
                            <th>Time (s)</th>
                            <th>Date</th>
                        </tr>
                    </thead>

                    <TransitionGroup name="rise" tag="tbody" :key="currentView">
                        <tr v-for="(entry, i) in topEntries" :key="entry.id || i" :class="{
                            'new-entry': newEntries.includes(entry.id),
                            'improved-entry': improvedEntries.includes(entry.id),
                        }">
                            <td>{{ i + 1 }}</td>
                            <td>{{ entry.name }}</td>
                            <td v-if="currentView === 'best'">{{ entry.match_type }}</td>
                            <td>{{ entry.time_seconds.toFixed(3) }}</td>
                            <td>{{ entry.date }}</td>
                        </tr>
                    </TransitionGroup>
                </table>


            </div>

            <!-- RIGHT: Live Timers -->
            <div class="live-section">
                <h2>🏁 Live Race Timers</h2>

                <TransitionGroup name="fade-match" tag="div" class="matches-container">
                    <div v-for="(match, matchId) in liveMatches" :key="matchId" class="match-block">
                        <h3>{{ match.match_type.toUpperCase() }}</h3>

                        <div v-if="match.match_type === 'solo'">
                            <div v-for="team in match.teams" :key="team.id" class="team-block">
                                <div v-for="player in team.players" :key="player.device_id" class="player-card"
                                    :class="{ foul: player.foul }">
                                    <strong v-if="player.player_name">{{ player.player_name }} — </strong>
                                    <strong>{{ player.device_id }}</strong> —
                                    <AnimatedTimer :time="player.time_seconds || 0"
                                        :rolling="player.status === 'drinking'" />
                                    <strong v-if="player.foul">FOUL</strong>
                                </div>
                            </div>
                        </div>

                        <div v-else>
                            <div v-for="(team, tIndex) in match.teams" :key="tIndex" class="team-block">
                                <h4>Team {{ team.name || tIndex + 1 }}</h4>
                                <div v-for="player in team.players" :key="player.device_id" class="player-card"
                                    :class="{ foul: player.foul }">
                                    <strong v-if="player.player_name">{{ player.player_name }} — </strong>
                                    <strong>{{ player.device_id }}</strong> —
                                    <AnimatedTimer :time="player.time_seconds || 0"
                                        :rolling="player.status === 'drinking'" />
                                    <strong v-if="player.foul">FOUL</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                </TransitionGroup>

            </div>
        </div>

    </main>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import logoURL from '../assets/f1.png'
import AnimatedTimer from '../components/AnimatedTimer.vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()
function homebut() {
    router.push("/")
}

const currentView = ref('solo')
const soloData = ref([])
const teamData = ref([])
const bestTimes = ref([])

const liveMatches = ref({}) // 🟢 Will hold the live matches from WS

async function fetchResults() {
    const [matchesRes, resultsRes, playersRes, teamsRes] = await Promise.all([
        axios.get('http://127.0.0.1:8000/data/matches'),
        axios.get('http://127.0.0.1:8000/data/results'),
        axios.get('http://127.0.0.1:8000/data/players'),
        axios.get('http://127.0.0.1:8000/data/teams'),
    ])

    const matches = matchesRes.data
    const results = resultsRes.data
    const players = playersRes.data
    const teams = teamsRes.data

    // 🚫 Filter out any result with foul = true
    const validResults = results.filter(r => !r.foul)

    // 🏎️ SOLO leaderboard
    const newSolo = validResults
        .filter(r => {
            const match = matches.find(m => m.id === r.match_id)
            return match && match.match_type === 'solo'
        })
        .map(r => ({
            id: r.id,
            name: players.find(p => p.id === r.player_id)?.name || 'Unknown',
            time_seconds: r.time_seconds,
            date: r.date
        }))
        .sort((a, b) => a.time_seconds - b.time_seconds)
        .slice(0, 10)

    // 🧑‍🤝‍🧑 TEAM leaderboard
    const teamResults = {}
    validResults.forEach(r => {
        const match = matches.find(m => m.id === r.match_id)
        if (match && match.match_type === '5v5') {
            if (!teamResults[r.team_id]) teamResults[r.team_id] = []
            teamResults[r.team_id].push(r.time_seconds)
        }
    })

    const newTeam = Object.entries(teamResults)
        .map(([team_id, times]) => {
            const teamEntries = validResults.filter(r => r.team_id === Number(team_id))
            const latestDate = teamEntries.length
                ? teamEntries.sort((a, b) => new Date(b.date) - new Date(a.date))[0].date
                : 'N/A'

            return {
                id: Number(team_id),
                name: teams.find(t => t.id === Number(team_id))?.name || 'Team',
                time_seconds: times.reduce((a, b) => a + b, 0) / times.length,
                date: latestDate,
            }
        })
        .sort((a, b) => a.time_seconds - b.time_seconds)
        .slice(0, 10)

    // 🔥 BEST overall (across all match types)
    const best = validResults
        .map(r => {
            const match = matches.find(m => m.id === r.match_id)
            const player = players.find(p => p.id === r.player_id)
            const team = teams.find(t => t.id === r.team_id)

            return {
                id: r.id,
                name: player?.name || team?.name || 'Unknown',
                match_type: match?.match_type?.toUpperCase() || 'UNKNOWN',
                time_seconds: r.time_seconds,
                date: r.date,
            }
        })
        .sort((a, b) => a.time_seconds - b.time_seconds)
        .slice(0, 10)

    bestTimes.value = best

    // 🧠 Only update if changed
    if (JSON.stringify(newSolo) !== JSON.stringify(soloData.value)) {
        soloData.value = newSolo
    }

    if (JSON.stringify(newTeam) !== JSON.stringify(teamData.value)) {
        teamData.value = newTeam
    }
}


function nextView() {
    if (currentView.value === 'solo') currentView.value = 'team'
    else if (currentView.value === 'team') currentView.value = 'best'
    else currentView.value = 'solo'
}

function prevView() {
    if (currentView.value === 'best') currentView.value = 'team'
    else if (currentView.value === 'team') currentView.value = 'solo'
    else currentView.value = 'best'
}




// 🧠 Computed
const topEntries = computed(() => {
    if (currentView.value === 'solo') return soloData.value
    if (currentView.value === 'team') return teamData.value
    return bestTimes.value
})
const currentViewTitle = computed(() => {
    if (currentView.value === 'solo') return '🏎️ Top 10 Players (Solo)'
    if (currentView.value === 'team') return '🏁 Top 10 Teams (5v5)'
    return '🔥 Best Overall Times'
})

const currentViewSubtitle = computed(() => {
    if (currentView.value === 'solo') return 'Fastest solo times'
    if (currentView.value === 'team') return 'Average team results'
    return 'Best performances across all match types'
})

// 🧩 WebSocket listener
function connectWS() {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws/matches')
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'matches_update') {
            const newData = msg.data

            // 🧩 Add or update existing matches
            for (const id in newData) {
                liveMatches.value[id] = newData[id]
            }

            // 🧹 Remove matches that disappeared (batch update for smooth fade)
            const updated = { ...liveMatches.value }
            let changed = false

            for (const id of Object.keys(liveMatches.value)) {
                if (!newData[id]) {
                    delete updated[id]
                    changed = true
                }
            }

            if (changed) {
                liveMatches.value = updated
            }


        }
    }

}

const isAutoSwitching = ref(true)
let switchInterval = null

function toggleAutoSwitch() {
    isAutoSwitching.value = !isAutoSwitching.value

    if (isAutoSwitching.value) {
        startAutoSwitch()
    } else {
        clearInterval(switchInterval)
        switchInterval = null
    }
}

function startAutoSwitch() {
    clearInterval(switchInterval)
    switchInterval = setInterval(nextView, 10000)
}

onMounted(() => {
    fetchResults()
    connectWS()
    setInterval(fetchResults, 15000)
    startAutoSwitch() // ✅ only runs when enabled
})


const previousEntries = ref([])
const newEntries = ref([])
const improvedEntries = ref([])

function trackChanges() {
    const currentIds = topEntries.value.map(e => e.id)
    const prevIds = previousEntries.value.map(e => e.id)

    // New entries that just appeared in Top 10
    newEntries.value = currentIds.filter(id => !prevIds.includes(id))

    // Entries that improved position
    improvedEntries.value = topEntries.value
        .filter((entry, idx) => {
            const prevIndex = previousEntries.value.findIndex(e => e.id === entry.id)
            return prevIndex !== -1 && prevIndex > idx
        })
        .map(e => e.id)

    // Store this frame
    previousEntries.value = JSON.parse(JSON.stringify(topEntries.value))

    // Clear highlights after animation
    setTimeout(() => {
        newEntries.value = []
        improvedEntries.value = []
    }, 2000)
}

// 🧩 Run tracker every time leaderboard updates
let lastView = currentView.value

watch(topEntries, () => {
    if (currentView.value === lastView) {
        trackChanges()
    }
    lastView = currentView.value
})


</script>

<style lang="scss" scoped>
button {
    background-color: #E10600;
    color: white;
    padding: 5px 10px;
    border-radius: 10px;
}

button:hover {
    background-color: #9d0600;
}



/* 🖼 Responsive logo */
.logo {
    display: flex;
    justify-content: center;
    align-items: center;
    width: 100%;
    padding: 20px 0;
}

.responsive-logo {
    width: 100%;
    max-width: 300px;
    /* optional: prevents it from getting too large on big screens */
    height: auto;
    /* keeps proportions */
    object-fit: contain;
}

@media (max-width: 768px) {
    .responsive-logo {
        max-width: 200px;
    }
}

h1,
p,
h2,
h3,
h4 {
    color: white;
}

#PositionsTable {
    width: 90%;
    border-collapse: collapse;
    margin: 20px auto;
}

#PositionsTable th {
    background-color: #E10600;
    color: white;
    padding: 8px;
}

#PositionsTable td {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    padding: 8px;
    text-align: center;
}

.scoreboard {
    width: 100%;
    text-align: center;
    padding-top: 20px;
    position: relative;
}

.header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 20px;
}

.titles {
    text-align: center;
    min-width: 250px;
}

.arrow-btn {
    background: none;
    border: 2px solid #E10600;
    color: #E10600;
    font-size: 1.5rem;
    border-radius: 10px;
    padding: 5px 10px;
    transition: 0.2s;
}

.arrow-btn:hover {
    background-color: #E10600;
    color: white;
    transform: scale(1.1);
}

.auto-switch-toggle {
    text-align: center;
    margin-top: 10px;
}

.auto-switch-toggle button {
    background-color: #222;
    border: 2px solid #E10600;
    color: #fff;
    padding: 6px 12px;
    border-radius: 10px;
    font-weight: 600;
    transition: 0.2s;
}

.auto-switch-toggle button:hover {
    background-color: #E10600;
    color: #fff;
}


/* 🟢 LIVE SECTION */
.live-section {
    margin-top: 40px;
    padding: 20px;
    text-align: center;
}

.match-block {
    border: 1px solid #E10600;
    border-radius: 15px;
    margin: 15px auto;
    padding: 15px;
    width: 90%;
    background: rgba(255, 255, 255, 0.05);
}

.team-block {
    margin-top: 10px;
    padding: 10px;
}

.player-card {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    margin: 5px auto;
    padding: 8px 15px;
    width: fit-content;
}

/* ✨ Fade animation */
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.8s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

/* ✨ Leaderboard rise & highlight animation */
.rise-enter-active,
.rise-leave-active {
    transition: all 3s ease;
}

.rise-enter-from {
    opacity: 0;
    transform: translateY(30px);
}

.rise-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}

/* Highlight for new or improved entries */
.new-entry {
    animation: highlight-green 4s ease;
}

.improved-entry {
    animation: highlight-blue 4s ease;
}

/* 🧩 Split layout stays inside viewport */
.content-wrapper {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    width: 100%;
    height: 100%;
    padding: 20px 40px;
    box-sizing: border-box;
    gap: 30px;
}


/* Left: Leaderboard — takes half screen */
.scoreboard {
    flex: 1;
    max-width: 50%;
    text-align: center;
    overflow: hidden;
    /* prevents table from expanding page */
}

/* Right: Live timers — scroll internally if needed */
.live-section {
    flex: 1;
    max-width: 50%;
    height: 100%;
    overflow-y: auto;
    /* allows scrolling inside only this panel */
    padding: 20px;
    text-align: center;
}

/* 🎬 Match fade-in / fade-out transitions */
.fade-match-enter-active {
    transition: all 2s ease;
}

.fade-match-leave-active {
    transition: opacity 1s ease, transform 1s ease, filter 1s ease;
}

.fade-match-enter-from {
    opacity: 0;
    transform: translateY(15px) scale(0.97);
}

.fade-match-leave-to {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
    filter: brightness(0.4);
}

/* Keep layout smooth during transition */
.matches-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

/* 🧱 Keep the same card look */
.match-block {
    border: 1px solid #E10600;
    border-radius: 15px;
    margin: 15px auto;
    padding: 15px;
    width: 90%;
    background: rgba(255, 255, 255, 0.05);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}




@keyframes highlight-green {
    0% {
        background-color: rgba(0, 255, 100, 0.4);
    }

    100% {
        background-color: rgba(255, 255, 255, 0.1);
    }
}

@keyframes highlight-blue {
    0% {
        background-color: rgba(0, 150, 255, 0.4);
    }

    100% {
        background-color: rgba(255, 255, 255, 0.1);
    }
}

/* 🚨 Smooth red blinking animation for fouls */
@keyframes foul-blink {

    0%,
    100% {
        background-color: rgba(255, 0, 0, 0.2);
        box-shadow: 0 0 5px rgba(255, 0, 0, 0.3);
    }

    50% {
        background-color: rgba(255, 0, 0, 0.5);
        box-shadow: 0 0 15px rgba(255, 0, 0, 0.7);
    }
}

/* Apply to player card when foul is true */
.player-card.foul {
    animation: foul-blink 1.2s ease-in-out infinite;
    border: 1px solid rgba(255, 0, 0, 0.6);
}


/* 🧱 Page fills screen — no body scroll */
#Public-page {
    font-family: "Titillium Web", sans-serif;
    height: 100vh;
    /* full viewport height */
    width: 100vw;
    /* full viewport width */
    overflow: hidden;
    /* disables scrollbars */
    display: flex;
    flex-direction: column;
    background:
        linear-gradient(27deg, #151515 5px, transparent 5px) 0 5px,
        linear-gradient(207deg, #151515 5px, transparent 5px) 10px 0px,
        linear-gradient(27deg, #222 5px, transparent 5px) 0px 10px,
        linear-gradient(207deg, #222 5px, transparent 5px) 10px 5px,
        linear-gradient(90deg, #1b1b1b 10px, transparent 10px),
        linear-gradient(#1d1d1d 25%, #1a1a1a 25%, #1a1a1a 50%, transparent 50%, transparent 75%, #242424 75%, #242424);
    background-color: #131313;
    background-size: 20px 20px;
}
</style>
