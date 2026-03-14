<template>
  <div class="h-full overflow-y-auto bg-gray-900 text-gray-300 py-4 font-mono text-sm border-r border-gray-700 select-none">
    <div v-if="loading" class="px-4 text-gray-500">Loading tree...</div>
    <div v-else>
      <TreeNode 
        v-if="rootNode" 
        :node="rootNode" 
        :selectedDn="selectedDn"
        @select="onSelect" 
        @action="onAction"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import TreeNode from './TreeNode.vue'

const props = defineProps({
  selectedDn: String
})

const emit = defineEmits(['select', 'action'])

const rootNode = ref(null)
const loading = ref(true)

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

function onSelect(dn) {
  emit('select', dn)
}

function onAction({ action, dn }) {
  emit('action', { action, dn })
}

onMounted(loadRoot)
</script>
