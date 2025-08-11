<template>
	<main id="Public-page">
        <div class="logo">
			<img :src="logoURL" alt="FINOS" /> 
		</div>
                <div>
        <button v-if="$route.meta.hideNav"  @click="homebut">Home</button>
        </div>
        <div>
            <div id="table_left">
                <h1>Race Results</h1>
                <p>Official times</p>
                <table id="PositionsTable">
                    <thead>
                        <tr>                    
                            <th>Position</th>
                            <th>Time</th>
                            <th>Name</th></tr>
                    </thead>
                </table>
            </div>
            <div id="table_right">
                <h1>games</h1>
            </div>
        </div>

	</main>
</template>

<script setup>
import logoURL from '../assets/f1.png'
import { useRouter } from 'vue-router';

const router= useRouter()


function homebut() {
  router.push("/")
}

</script>

<style lang="scss" scoped>
button{
    background-color: #E10600;
    color: white;
    padding: 5px 10px;
    border-radius: 10px;
}
button:hover{
    background-color: #9d0600;

}
img{
    max-height: 150px;
}
h1, p{
    color: white;

}
#PositionsTable{
    width: 80%;

}
#PositionsTable th{
    background-color: #E10600;
    color: white;


}

#table_left{
width: 80%;
float: left;
}
#table_right{
width: 20%;
float: right;
}
#Public-page{
    font-family: "Titillium Web", sans-serif;
  min-height: 100vh; /* Viewport height */
  width: 100%;
    background:
    linear-gradient(27deg, #151515 5px, transparent 5px) 0 5px,
    linear-gradient(207deg, #151515 5px, transparent 5px) 10px 0px,
    linear-gradient(27deg, #222 5px, transparent 5px) 0px 10px,
    linear-gradient(207deg, #222 5px, transparent 5px) 10px 5px,
    linear-gradient(90deg, #1b1b1b 10px, transparent 10px),
    linear-gradient(#1d1d1d 25%, #1a1a1a 25%, #1a1a1a 50%, transparent 50%, transparent 75%, #242424 75%, #242424);
  background-color: #131313;
  background-size: 20px 20px;
}
</style>