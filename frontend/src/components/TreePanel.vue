<template>
  <div class="h-full flex flex-col bg-gray-900 text-gray-300 font-mono text-sm border-r border-gray-700 select-none">
    <!-- Search bar -->
    <div class="px-3 py-3 border-b border-gray-700">
      <div class="relative">
        <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">🔍</span>
        <input 
          v-model="searchQuery" 
          placeholder="Filter tree..." 
          class="w-full bg-gray-800 border border-gray-700 rounded pl-8 pr-8 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
          @keydown.escape="searchQuery = ''"
        />
        <button v-if="searchQuery" @click="searchQuery = ''" class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs">✕</button>
      </div>
    </div>

    <!-- Tree content -->
    <div class="flex-1 overflow-y-auto py-2">
      <div v-if="loading" class="px-4 text-gray-500 flex items-center gap-2">
        <span class="animate-spin">⟳</span> Loading tree...
      </div>
      <div v-else>
        <TreeNode 
          v-if="rootNode" 
          :node="rootNode" 
          :selectedDn="selectedDn"
          :searchQuery="searchQuery"
          @select="onSelect" 
          @action="onAction"
          @move="onMove"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiV2 as api } from '../api/client'
import TreeNode from './TreeNode.vue'

const props = defineProps({
  selectedDn: String
})

const emit = defineEmits(['select', 'action', 'move'])

const rootNode = ref(null)
const loading = ref(true)
const searchQuery = ref('')

async function loadRoot() {
  try {
    const { data } = await api.get('/tree/root')
    rootNode.value = data
  } catch (e) {
    console.error('Failed to load tree root', e)
  } finally {
    loading.value = false
  }
}

function onSelect(dn) { emit('select', dn) }
function onAction({ action, dn }) { emit('action', { action, dn }) }
function onMove(payload) { emit('move', payload) }

onMounted(loadRoot)
</script>
