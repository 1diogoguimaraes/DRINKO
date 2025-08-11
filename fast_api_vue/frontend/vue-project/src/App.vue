<template>
  <div>
    <h1>ESP32 Device Status</h1>
    <ul>
      <li v-for="(info, id) in statuses" :key="id">
        <strong>{{ id }}</strong>,
        Status: {{ info.status }},
        Mode: {{ info.mode }},
        Team: {{ info.team }},
        Relay Position: {{ info.relay_pos }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { reactive, onMounted, onBeforeUnmount } from 'vue'

const statuses = reactive({})
let socket = null

onMounted(() => {
  socket = new WebSocket("ws://localhost:8000/ws/live")

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'status') {
    // Save all the fields for each device
      statuses[data.device_id] = {
        status: data.status,
        mode: data.mode,
        team: data.team,
        relay_pos: data.relay_pos
     }
    }
  } 

  socket.onclose = () => {
    console.warn("WebSocket disconnected.")
  }
})

onBeforeUnmount(() => {
  if (socket) socket.close()
})
</script>
