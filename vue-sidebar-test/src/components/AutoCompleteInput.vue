<template>
    <div class="relative w-full">
        <!-- 🔹 Input -->
        <input v-model="query" @focus="showList = true" @input="$emit('update:modelValue', query)" @blur="onBlur"
            :placeholder="placeholder" ref="inputRef" class="w-full p-2.5 rounded-md bg-gray-800 text-white border border-gray-600 
             focus:outline-none focus:ring-2 focus:ring-red-600 transition-all duration-200" />

        <!-- 🔹 Dropdown (teleported to body so it’s above modals) -->
        <teleport to="body">
            <transition name="fade-scale">
                <ul v-if="showList && filtered.length" class="autocomplete-dropdown" :style="dropdownStyle">
                    <li v-for="(name, i) in filtered" :key="i" class="autocomplete-item"
                        @mousedown.prevent="selectName(name)">
                        {{ name }}
                    </li>
                </ul>
            </transition>
        </teleport>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue"

const props = defineProps({
    modelValue: String,
    suggestions: Array,
    placeholder: String,
})
const emit = defineEmits(["update:modelValue"])

const query = ref(props.modelValue || "")
const showList = ref(false)
const inputRef = ref(null)
const dropdownStyle = ref({})

const filtered = computed(() =>
    !query.value
        ? []
        : props.suggestions.filter((s) =>
            s.toLowerCase().includes(query.value.toLowerCase())
        )
)

function positionDropdown() {
    const input = inputRef.value
    if (!input) return
    const rect = input.getBoundingClientRect()
    dropdownStyle.value = {
        top: `${rect.bottom + window.scrollY + 4}px`,
        left: `${rect.left + window.scrollX}px`,
        width: `${rect.width}px`,
        position: "absolute",
        zIndex: 9999,
    }
}

function selectName(name) {
    query.value = name
    emit("update:modelValue", name)
    showList.value = false
}

function onBlur() {
    // Delay to allow clicking a suggestion before it disappears
    window.setTimeout(() => (showList.value = false), 150)
}

onMounted(() => {
    window.addEventListener("scroll", positionDropdown)
    window.addEventListener("resize", positionDropdown)
})
onBeforeUnmount(() => {
    window.removeEventListener("scroll", positionDropdown)
    window.removeEventListener("resize", positionDropdown)
})

watch(showList, (val) => {
    if (val) nextTick(positionDropdown)
})
watch(
    () => props.modelValue,
    (val) => (query.value = val)
)
</script>

<style scoped>
/* 🔹 Fade animation */
.fade-scale-enter-active,
.fade-scale-leave-active {
    transition: all 0.2s ease;
}

.fade-scale-enter-from {
    opacity: 0;
    transform: scale(0.97) translateY(-4px);
}

.fade-scale-leave-to {
    opacity: 0;
    transform: scale(0.97) translateY(-4px);
}

/* 🔹 Dropdown container */
.autocomplete-dropdown {
    background-color: #111;
    /* fully opaque black */
    border: 1px solid #444;
    border-radius: 6px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
    overflow: hidden;
    max-height: 200px;
    overflow-y: auto;
    position: absolute;
}

/* 🔹 Items */
.autocomplete-item {
    padding: 0.5rem 0.75rem;
    color: #ddd;
    font-size: 0.9rem;
    cursor: pointer;
    user-select: none;
    background-color: #111;
    transition: background-color 0.15s, color 0.15s, transform 0.1s;
}

/* Hover + Active feedback */
.autocomplete-item:hover {
    background-color: #e10600;
    /* red hover */
    color: #fff;
}

.autocomplete-item:active {
    transform: scale(0.98);
}

/* 🔹 Scrollbar styling */
.autocomplete-dropdown::-webkit-scrollbar {
    width: 6px;
}

.autocomplete-dropdown::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 3px;
}

.autocomplete-dropdown::-webkit-scrollbar-thumb:hover {
    background: #666;
}
</style>
