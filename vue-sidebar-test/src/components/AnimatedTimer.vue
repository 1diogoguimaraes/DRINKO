<template>
    <div class="timer">
        <div v-for="(digit, index) in displayDigits" :key="index" class="digit-wrapper">
            <div v-if="digit === '.'" class="dot">.</div>

            <div v-else class="digit-reel" :style="{ transform: `translateY(${-digitOffsets[index] * 1.5}em)` }">
                <div v-for="n in 10" :key="n" class="digit">{{ (n - 1) }}</div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from "vue"

const props = defineProps({
    time: { type: Number, default: 0 },
    rolling: { type: Boolean, default: false },
})

const displayDigits = ref(["0", "0", ".", "0", "0", "0"])
const digitOffsets = ref(displayDigits.value.map(() => 0))

let reels = []
let frameIds = []

// 🎯 Utility — format time into ['0','2','.', '2','6','6']
function formatTime(t) {
    return t.toFixed(3).padStart(6, "0").split("")
}

// 🎞️ Start spinning each reel staggered, right to left, with acceleration
function startRolling() {
    stopAll()
    const digits = displayDigits.value
    const total = digits.length

    digits.forEach((digit, i) => {
        if (digit === ".") return // skip dot reel

        const index = i
        const startDelay = (total - i) * 100 // ms, right → left delay
        setTimeout(() => startReel(index), startDelay)
    })
}

function startReel(index) {
    let speed = 0.5
    let velocity = 0.1 // acceleration
    let pos = 0

    const update = () => {
        speed = Math.min(speed + velocity, 1.5) // accelerate
        pos = (pos + speed * 0.3) % 10
        digitOffsets.value[index] = pos
        frameIds[index] = requestAnimationFrame(update)
    }

    reels[index] = { running: true, stop: false }
    update()
}

// 🧠 Smooth stop right → left, with deceleration
function stopRolling(newTime) {
    const digits = formatTime(newTime)
    const total = digits.length

    digits.forEach((d, i) => {
        if (d === ".") return // skip dot
        const index = i
        const stopDelay = (total - i) * 250 // right → left
        setTimeout(() => stopReel(index, Number(d)), stopDelay)
    })
}

function stopReel(index, finalDigit) {
    const reel = reels[index]
    if (!reel) return

    reel.stop = true
    let speed = 1.5

    const decelerate = () => {
        if (speed > 0.05) {
            speed *= 0.9 // decelerate gradually
            digitOffsets.value[index] = (digitOffsets.value[index] + speed * 0.3) % 10
            frameIds[index] = requestAnimationFrame(decelerate)
        } else {
            // Snap to final digit
            digitOffsets.value[index] = finalDigit
            cancelAnimationFrame(frameIds[index])
        }
    }

    decelerate()
}

function stopAll() {
    frameIds.forEach((id) => cancelAnimationFrame(id))
    reels = []
}

// 🧩 Watch props
watch(
    () => props.rolling,
    (val) => {
        if (val) startRolling()
        else stopRolling(props.time)
    },
    { immediate: true }
)

watch(
    () => props.time,
    (val) => {
        if (!props.rolling) stopRolling(val)
    }
)

onBeforeUnmount(() => stopAll())
</script>

<style scoped>
.timer {
    display: inline-flex;
    align-items: center;
    font-family: monospace;
    font-size: 1.4rem;
    color: white;
}

.digit-wrapper {
    width: 1ch;
    height: 1.5em;
    overflow: hidden;
    display: inline-block;
    margin: 0 1px;
    position: relative;
}

.digit-reel {
    display: flex;
    flex-direction: column;
    transition: transform 0.1s linear;
    will-change: transform;
}

.digit {
    height: 1.5em;
    text-align: center;
}

.dot {
    display: inline-block;
    width: 1ch;
    text-align: center;
    height: 1.5em;
}

.unit {
    margin-left: 4px;
    font-size: 0.9rem;
    opacity: 0.8;
}
</style>
