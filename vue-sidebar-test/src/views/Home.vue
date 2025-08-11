<template>
	<main id="Home-page">
		<h1>Home</h1>
		<p>This is the home page</p>
		<StatusTable :statusData="statusData"/>
	</main>
</template>

<script setup>
import StatusTable from '../components/StatusTable.vue';
import { reactive } from 'vue';

const statusData = reactive([
	{id:1,state:'ready',mode:'single'},
	{id:3,state:'ready',mode:'1v1'}
]);




</script>