<template>
	<main id="Table-page">
		<h1>Table</h1>
		<p>This is the table page</p>
		<StandartTable :data="customersData"/>
	</main>
</template>

<script setup>

import StandartTable from '../components/StandartTable.vue';
import { reactive } from 'vue'

const customersData = reactive([
  { id: 1, company: 'Alfreds Futterkiste', contact: 'Maria Anders', country: 'Germany' },
  { id: 2, company: 'Berglunds snabbköp', contact: 'Christina Berglund', country: 'Sweden' },
  { id: 3, company: 'Centro comercial Moctezuma', contact: 'Francisco Chang', country: 'Mexico' },
  { id: 4, company: 'Ernst Handel', contact: 'Roland Mendel', country: 'Austria' },
  { id: 5, company: 'Island Trading', contact: 'Helen Bennett', country: 'UK' },
  { id: 6, company: 'Königlich Essen', contact: 'Philip Cramer', country: 'Germany' },
  { id: 7, company: 'Laughing Bacchus Winecellars', contact: 'Yoshi Tannamuri', country: 'Canada' },
  { id: 8, company: 'Magazzini Alimentari Riuniti', contact: 'Giovanni Rovelli', country: 'Italy' }
]);



</script>

<style lang="scss" scoped>

</style>
