<template>
	<main id="Settings-page">
		<h1>Settings</h1>
		<p>This is the settings page</p>

		<div class="dark-toggle" @click="toggleDarkMode">
			<span class="material-icons icon">
				{{ isDark ? 'dark_mode' : 'light_mode' }}
			</span>
			<div class="switch" :class="{ active: isDark }">
				<div class="slider"></div>
			</div>
		</div>
	</main>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const isDark = ref(false)

onMounted(() => {
	isDark.value = localStorage.getItem('darkMode') === 'true'
	updateDarkClass()
})

const toggleDarkMode = () => {
	isDark.value = !isDark.value
	localStorage.setItem('darkMode', isDark.value)
	updateDarkClass()
}

const updateDarkClass = () => {
	if (isDark.value) {
		document.documentElement.classList.add('dark-mode')
	} else {
		document.documentElement.classList.remove('dark-mode')
	}
}
</script>

<style scoped>
.dark-toggle {
	display: flex;
	align-items: center;
	gap: 1rem;
	cursor: pointer;
	user-select: none;
}

.icon {
	font-size: 2rem;
	color: var(--primary);
	transition: color 0.3s ease;
}

.switch {
	width: 50px;
	height: 26px;
	background: var(--grey);
	border-radius: 50px;
	position: relative;
	transition: background 0.3s ease;
}

.switch.active {
	background: var(--primary);
}

.slider {
	width: 22px;
	height: 22px;
	background: white;
	border-radius: 50%;
	position: absolute;
	top: 2px;
	left: 2px;
	transition: transform 0.3s ease;
}

.switch.active .slider {
	transform: translateX(24px);
}
</style>
