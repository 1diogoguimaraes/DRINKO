<template>
	<main id="Home-page">
		<h1>Home</h1>
		<p>This is the home page</p>
		<StatusTable :data="statusData"/>
	</main>
</template>

<script setup>
import StatusTable from '../components/StatusTable.vue';
import { reactive, onMounted, onBeforeUnmount } from 'vue'


const statusData = reactive([
	{id:1,state:'ready',mode:'single'},
	{id:3,state:'ready',mode:'1v1'}
]);

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