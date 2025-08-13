<template>
	<div class="app">
		<!-- Sidebar -->
		<Sidebar v-if="!$route.meta.hideNav" />

		<!-- Content -->
		<router-view />
	</div>
</template>

<script setup>
import Sidebar from './components/sidebar/Sidebar.vue'


</script>
<style lang="scss">
:root {
	--primary: #41B883;
	--primary-alt: #18b870;
	--secondary:#34495E;
	--grey: #64748b;
	--dark: #1e293b;
	--dark-alt: #334155;
	--light: #f1f5f9;
	--text-color: #000;
}

/* Dark mode overrides */
.dark-mode {
	--light: #0f172a;
	--dark: #f1f5f9;
	--dark-alt: #e2e8f0;
	--text-color: #f1f5f9;
}

* {
	margin: 0;
	padding: 0;
	box-sizing: border-box;
	font-family: 'Fira sans', sans-serif;
}

body {
	background: var(--light);
	color: var(--text-color);
}

button {
	cursor: pointer;
	appearance: none;
	border: none;
	outline: none;
	background: none;
}

.app {
	display: flex;

	main {
		flex: 1 1 0;
		padding: 2rem;

		@media (max-width: 1024px) {
			padding-left: 6rem;
		}
	}
}
</style>
