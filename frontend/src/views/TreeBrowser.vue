<template>
  <div class="flex h-full w-full bg-gray-50">
    
    <!-- Sidebar / Tree Panel -->
    <div class="w-80 flex-shrink-0 border-r border-gray-200">
      <TreePanel 
        :selectedDn="selectedDn"
        @select="onNodeSelect"
        @action="onNodeAction"
        :key="treeKey"
      />
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col items-center justify-center bg-gray-100 text-gray-500" v-if="!selectedDn && !creatingMode">
      <div class="text-4xl mb-4">🌳</div>
      <h2 class="text-xl font-semibold mb-2">LDAP Directory Browser</h2>
      <p>Select a node from the tree to view its details, or right-click to add an entry.</p>
    </div>

    <div class="flex-1 overflow-hidden" v-else-if="creatingMode">
      <CreateEntry 
        :parentDn="targetParentDn" 
        @cancel="creatingMode = false"
        @created="onEntryCreated"
      />
    </div>

    <div class="flex-1 overflow-hidden" v-else>
      <EntryDetail 
        :dn="selectedDn" 
        @delete="onEntryDelete"
      />
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api/client'
import TreePanel from '../components/TreePanel.vue'
import EntryDetail from '../components/EntryDetail.vue'
import CreateEntry from '../components/CreateEntry.vue'

const selectedDn = ref('')
const creatingMode = ref(false)
const targetParentDn = ref('')
const treeKey = ref(0) // used to force re-render tree panel on structural changes

function onNodeSelect(dn) {
  selectedDn.value = dn
  creatingMode.value = false
}

function onNodeAction({ action, dn }) {
  if (action === 'create') {
    targetParentDn.value = dn
    creatingMode.value = true
    selectedDn.value = ''
  } else if (action === 'delete') {
    promptDelete(dn)
  }
}

async function promptDelete(dn) {
  if (confirm(`Are you sure you want to delete ${dn}?\n\nCAUTION: Once deleted it cannot be restored.`)) {
    const isRecursive = confirm(`If ${dn} has children, do you want to recursively delete the whole subtree?\n\nSelect 'Cancel' (No) to only delete if it has no children.`)
    try {
      await api.delete('/entry', { params: { dn, recursive: isRecursive }})
      treeKey.value++ // refresh tree
      selectedDn.value = ''
    } catch (e) {
      alert('Delete failed: ' + (e.response?.data?.detail || e.message))
    }
  }
}

function onEntryDelete(dn) {
  promptDelete(dn)
}

function onEntryCreated() {
  creatingMode.value = false
  treeKey.value++ // refresh tree to show new node
}
</script>
