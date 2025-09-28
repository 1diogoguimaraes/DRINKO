<script setup>
import StandartTable from '../components/StandartTable.vue';
import { reactive, onMounted, onBeforeUnmount, computed } from 'vue'

const statuses = reactive({})   // device_id → data
let socket = null

onMounted(() => {
  socket = new WebSocket("ws://localhost:8000/ws/live")

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'status') {
      statuses[data.device_id] = {
        device_id: data.device_id, // keep id inside row
        status: data.status,
        match:data.match_id,
        mode: data.mode,
        team: Number(data.team),
        relay_pos: data.relay_pos,
        battery: data.battery
      }
      statuses[data.device_id] = { ...statuses[data.device_id] }
    }
  } 

  socket.onclose = () => {
    console.warn("WebSocket disconnected.")
  }
})

onBeforeUnmount(() => {
  if (socket) socket.close()
})

// 🔹 computed array for table
const statusArray = computed(() => Object.values(statuses))
</script>

<template>
	<main id="Home-page">
		<h1>Home</h1>
		<p>This is the home page</p>
		<StandartTable :data="statusArray"/>
	</main>
</template>
