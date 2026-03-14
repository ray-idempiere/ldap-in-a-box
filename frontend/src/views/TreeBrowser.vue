<template>
  <div class="flex h-full w-full bg-gray-950">
    
    <!-- Sidebar / Tree Panel -->
    <div class="w-80 flex-shrink-0">
      <TreePanel 
        :selectedDn="selectedDn"
        @select="onNodeSelect"
        @action="onNodeAction"
        @move="onNodeMove"
        :key="treeKey"
      />
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      
      <!-- Breadcrumb Bar -->
      <div v-if="selectedDn || creatingMode" class="flex items-center gap-1 px-4 py-2 bg-gray-900 border-b border-gray-800 text-sm flex-shrink-0">
        <span class="text-gray-500 mr-1">📍</span>
        <template v-for="(segment, idx) in breadcrumbs" :key="idx">
          <span v-if="idx > 0" class="text-gray-600 mx-0.5">›</span>
          <button 
            @click="navigateToBreadcrumb(idx)" 
            class="text-gray-400 hover:text-indigo-400 hover:underline transition-colors truncate max-w-[200px]"
            :class="{ 'text-indigo-300 font-medium': idx === breadcrumbs.length - 1 }"
            :title="segment.dn"
          >{{ segment.label }}</button>
        </template>
      </div>

      <!-- Empty state -->
      <div class="flex-1 flex flex-col items-center justify-center text-gray-500" v-if="!selectedDn && !creatingMode">
        <div class="text-6xl mb-6 opacity-50">🌳</div>
        <h2 class="text-xl font-semibold mb-2 text-gray-400">LDAP Directory Browser</h2>
        <p class="text-gray-600 text-sm">Select a node from the tree, or right-click to add an entry.</p>
        <div class="mt-8 flex gap-4 text-xs text-gray-600">
          <kbd class="px-2 py-1 bg-gray-800 rounded border border-gray-700">Ctrl+N</kbd> New Entry
          <kbd class="px-2 py-1 bg-gray-800 rounded border border-gray-700">Ctrl+S</kbd> Save
          <kbd class="px-2 py-1 bg-gray-800 rounded border border-gray-700">Del</kbd> Delete
        </div>
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
          ref="entryDetailRef"
          :dn="selectedDn" 
          @delete="onEntryDelete"
        />
      </div>
    </div>

    <!-- Toast container -->
    <div v-if="toast" class="fixed bottom-6 right-6 z-50 px-5 py-3 rounded-lg shadow-lg text-sm font-medium animate-slide-up"
      :class="toast.type === 'success' ? 'bg-green-900 text-green-200 border border-green-700' : 'bg-red-900 text-red-200 border border-red-700'">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiV2 as api } from '../api/client'
import TreePanel from '../components/TreePanel.vue'
import EntryDetail from '../components/EntryDetail.vue'
import CreateEntry from '../components/CreateEntry.vue'

const selectedDn = ref('')
const creatingMode = ref(false)
const targetParentDn = ref('')
const treeKey = ref(0)
const toast = ref(null)
const entryDetailRef = ref(null)

// Breadcrumbs
const breadcrumbs = computed(() => {
  const dn = creatingMode.value ? targetParentDn.value : selectedDn.value
  if (!dn) return []
  const parts = dn.split(',')
  const crumbs = []
  for (let i = 0; i < parts.length; i++) {
    crumbs.push({
      label: parts[i],
      dn: parts.slice(i).join(',')
    })
  }
  return crumbs.reverse()
})

function navigateToBreadcrumb(idx) {
  const crumb = breadcrumbs.value[idx]
  if (crumb) {
    selectedDn.value = crumb.dn
    creatingMode.value = false
  }
}

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 3000)
}

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

async function onNodeMove({ sourceDn, targetDn }) {
  const rdnPart = sourceDn.split(',')[0]
  if (confirm(`Move "${rdnPart}" to "${targetDn}"?\n\nThis will relocate the entry and all its children.`)) {
    try {
      // Extract RDN and new parent
      await api.post('/entry/move', { dn: sourceDn, new_parent_dn: targetDn })
      treeKey.value++
      showToast('success', `✅ Moved ${rdnPart} successfully`)
    } catch (e) {
      showToast('error', '❌ Move failed: ' + (e.response?.data?.detail || e.message))
    }
  }
}

async function promptDelete(dn) {
  if (confirm(`Are you sure you want to delete?\n\n${dn}\n\n⚠️ This cannot be undone.`)) {
    const rdnPart = dn.split(',')[0]
    try {
      await api.delete('/entry', { params: { dn, recursive: true }})
      treeKey.value++
      selectedDn.value = ''
      showToast('success', `🗑 Deleted ${rdnPart}`)
    } catch (e) {
      showToast('error', '❌ Delete failed: ' + (e.response?.data?.detail || e.message))
    }
  }
}

function onEntryDelete(dn) {
  promptDelete(dn)
}

function onEntryCreated() {
  creatingMode.value = false
  treeKey.value++
  showToast('success', '✅ Entry created successfully')
}

// Keyboard shortcuts
function onKeyDown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault()
    if (selectedDn.value) {
      onNodeAction({ action: 'create', dn: selectedDn.value })
    }
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (entryDetailRef.value?.saveChanges) {
      entryDetailRef.value.saveChanges()
    }
  }
  if (e.key === 'Delete' && selectedDn.value) {
    promptDelete(selectedDn.value)
  }
  if (e.key === 'Escape') {
    if (creatingMode.value) {
      creatingMode.value = false
    }
  }
}

onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<style>
@keyframes slide-up {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
.animate-slide-up { animation: slide-up 0.3s ease-out; }
</style>
