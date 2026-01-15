import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import TableView from '../views/TableView.vue'
import SettingsView from '../views/SettingsView.vue'
import PublicView from '../views/PublicView.vue'

const router = createRouter({
	history: createWebHistory(),
	routes: [
		{
			path: '/',
			name: 'Home',
			component: Home
		},
		{
			path: '/control',
			component: () => import('../views/Control.vue')
		},
		{
			path: '/table',
			name: 'Table',
			component: TableView
		}, {
			path: '/settings',
			name: 'Settings',
			component: SettingsView
		}, {
			path: '/public',
			name: 'Public',
			component: PublicView, meta: { hideNav: true }
		},

	],
})

export default router