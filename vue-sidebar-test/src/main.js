import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 1️⃣ Create your Vue app
const app = createApp(App)

// 2️⃣ Create and register Pinia
const pinia = createPinia()
app.use(pinia)

// 3️⃣ Add the router
app.use(router)

// 4️⃣ Mount the app
app.mount('#app')

// Optional: export the pinia instance if needed elsewhere
export { pinia }
