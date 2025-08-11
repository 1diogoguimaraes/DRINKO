<template>
    <div class="status-table">
        <div>
            <table id="customers">
                <thead>
                <tr>
                <th v-for="head in headers" :key="head">
                  {{ head }}
                </th>
                </tr>
                </thead>
                <tbody>
                  <tr v-for="(row,rowIndex) in data" :key="rowIndex">
                    <td v-for="key in headers" :key="key">
                      {{ row[key] }}
                    </td>                 
                  </tr>
                </tbody>
            </table>
        </div>
    </div>
    
</template>

<script setup>
import { computed } from 'vue';


const props = defineProps({data:{
  type:Array,
  required:true
}})

const headers= computed(()=> 
  props.data.length > 0 ? Object.keys(props.data[0]):[]
)




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