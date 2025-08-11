<template>
    <div class="status-table">
        <div>
            <table id="customers">
                <thead>
                <tr>
                    <th>ID</th>
                    <th>State</th>
                    <th>Mode</th>
                </tr>
                </thead>
                <tbody>
                <tr v-for="status in statusData" :key="status.id">
                    <td>{{ status.id }}</td>
                <td>{{ status.state }}</td>
                <td>{{ status.mode }}</td>
                </tr>
                </tbody>
            </table>
        </div>
    </div>
    
</template>

<script setup>

const props = defineProps(['statusData'])


</script>

<style lang="scss" scoped>
#customers {
  font-family: Arial, Helvetica, sans-serif;
  border-collapse: collapse;
  width: 100%;
}

#customers td, #customers th {
  border: 1px solid #ddd;
  padding: 8px;
}

#customers tr:nth-child(even){background-color: #f2f2f2;}

#customers tr:hover {background-color: #ddd;}

#customers th {
  padding-top: 12px;
  padding-bottom: 12px;
  text-align: left;
  background-color: #04AA6D;
  color: white;
}
</style>