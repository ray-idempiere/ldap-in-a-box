<template>
  <div class="h-full flex flex-col bg-gray-900 text-gray-300 font-mono text-sm border-r border-gray-700 select-none">
    <div class="px-3 py-3 border-b border-gray-700">
      <div class="flex items-center gap-2">
        <div class="relative flex-1">
          <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs">🔍</span>
          <input 
            v-model="searchQuery" 
            placeholder="Filter tree..." 
            class="w-full bg-gray-800 border border-gray-700 rounded pl-8 pr-8 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            @keydown.escape="clearSearch"
          />
          <button v-if="searchQuery" @click="clearSearch" class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs">✕</button>
        </div>
        <button @click="showAdvanced = !showAdvanced" class="bg-gray-800 border border-gray-700 hover:bg-gray-700 text-gray-300 p-1.5 rounded transition-colors" title="Advanced Search">
          ⚙️
        </button>
      </div>

      <div v-if="showAdvanced" class="mt-3">
        <TreeSearchBuilder @search="onAdvancedSearch" @close="showAdvanced = false" />
      </div>
    </div>

    <!-- Tree content / Search Results -->
    <div class="flex-1 overflow-y-auto py-2">
      <div v-if="isSearching" class="px-4 text-gray-500 flex items-center gap-2">
        <span class="animate-spin">⟳</span> Searching...
      </div>
      <div v-else-if="searchResults">
        <div class="px-3 py-2 flex items-center justify-between">
          <span class="text-xs text-gray-500 font-semibold uppercase tracking-wider">Search Results ({{ searchResults.length }})</span>
          <button @click="clearSearch" class="text-xs text-indigo-400 hover:text-indigo-300">Clear</button>
        </div>
        <div 
          v-for="res in searchResults" 
          :key="res.dn"
          class="px-4 py-2 hover:bg-gray-800 cursor-pointer text-sm truncate border-l-2"
          :class="selectedDn === res.dn ? 'bg-indigo-900/50 text-indigo-300 border-indigo-500' : 'text-gray-300 border-transparent'"
          @click="onSelect(res.dn)"
          :title="res.dn"
        >
          <div class="font-bold text-gray-200">{{ res.rdn }}</div>
          <div class="text-xs text-gray-500 truncate" :title="res.dn">{{ res.dn }}</div>
        </div>
        <div v-if="searchResults.length === 0" class="px-4 py-4 text-gray-500 italic text-sm">
          No entries found matching filter.
        </div>
      </div>
      <div v-else-if="loading" class="px-4 text-gray-500 flex items-center gap-2">
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
import TreeSearchBuilder from './TreeSearchBuilder.vue'

const props = defineProps({
  selectedDn: String
})

const emit = defineEmits(['select', 'action', 'move'])

const rootNode = ref(null)
const loading = ref(true)
const searchQuery = ref('')

const showAdvanced = ref(false)
const isSearching = ref(false)
const searchResults = ref(null)

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = null
}

async function onAdvancedSearch(filter) {
  if (!rootNode.value) return
  isSearching.value = true
  searchResults.value = null
  try {
    const { data } = await api.get('/tree/search', {
      params: { base_dn: rootNode.value.dn, filter }
    })
    searchResults.value = data
  } catch (e) {
    alert('Search failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    isSearching.value = false
  }
}

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
