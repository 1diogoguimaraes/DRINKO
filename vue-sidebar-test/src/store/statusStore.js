// src/store/statusStore.js
import { reactive } from 'vue'

export const statusStore = reactive({
    statuses: {},
    socket: null
})

export function initStatusSocket() {
    if (statusStore.socket) return  // already connected

    statusStore.socket = new WebSocket("ws://localhost:8000/ws/live")

    statusStore.socket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'status') {
            statusStore.statuses[data.device_id] = {
                status: data.status,
                mode: data.mode,
                team: data.team,
                relay_pos: data.relay_pos,
                battery: data.battery
            }
        }
    }

    statusStore.socket.onclose = () => {
        console.warn("WebSocket disconnected.")
        statusStore.socket = null
    }
}
