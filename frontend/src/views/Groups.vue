<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Groups</h1>
      <button @click="showCreate = true" class="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg transition-colors shadow">+ New Group</button>
    </div>

    <!-- Bulk Actions -->
    <div class="flex items-center gap-3 mb-4">
      <transition name="fade">
        <div v-if="selectedCns.length > 0" class="flex items-center gap-3 bg-indigo-900/30 border border-indigo-800/50 rounded-lg px-4 py-2">
          <span class="text-indigo-300 text-sm font-medium">{{ selectedCns.length }} selected</span>
          <div class="h-4 w-px bg-indigo-800 mx-1"></div>
          <button @click="bulkDelete" :disabled="isBulkActioning" class="text-sm bg-red-900/50 text-red-300 hover:bg-red-800/80 px-3 py-1 rounded transition-colors disabled:opacity-50 flex items-center gap-1">
            <span v-if="isBulkActioning" class="animate-spin inline-block w-3 h-3 border-2 border-red-300 border-t-transparent rounded-full"></span>
            🗑 Delete
          </button>
          <button @click="selectedCns = []" class="text-sm text-gray-400 hover:text-gray-200 px-2 py-1">Cancel</button>
        </div>
      </transition>
    </div>

    <div class="space-y-4">
      <!-- Select All row -->
      <div v-if="groups.length > 0" class="flex items-center px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg text-sm text-gray-400">
        <input type="checkbox" :checked="allSelected" @change="toggleAll" class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-900 mr-3" />
        <span @click="toggleAll({target: {checked: !allSelected}})" class="cursor-pointer select-none">Select All Groups</span>
      </div>


      <div v-for="g in groups" :key="g.cn" class="bg-gray-900 border border-gray-800 p-4 rounded-xl shadow-lg hover:border-gray-700 transition-colors">
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <input type="checkbox" :value="g.cn" v-model="selectedCns" class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-900 mr-4" />
            <span class="font-bold text-lg text-indigo-300 tracking-wide">{{ g.cn }}</span>
            <span class="text-gray-500 ml-3 text-sm">{{ g.description }}</span>
          </div>
          <span class="text-gray-400">{{ g.members.length }} members</span>
        </div>
        <div class="mt-3">
          <span v-for="m in g.members" :key="m" class="inline-block bg-indigo-900/40 border border-indigo-800 text-indigo-200 rounded-md px-2 py-0.5 text-xs mr-2 mb-2 tracking-wide font-mono">{{ m }}</span>
        </div>
        <div class="mt-3 flex gap-2">
          <input v-model="memberInputs[g.cn]" placeholder="Add member (uid)" class="bg-gray-950 border border-gray-800 text-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-1 focus:ring-indigo-500 outline-none w-64" />
          <button @click="addMember(g.cn)" class="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-1.5 rounded-lg text-sm transition-colors">Add</button>
        </div>
      </div>
    </div>

    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <form @submit.prevent="createGroup" class="bg-gray-900 border border-gray-800 p-6 rounded-xl w-96 shadow-2xl">
        <h2 class="text-xl font-bold mb-5 text-gray-100">New Group</h2>
        <div class="space-y-3">
          <input v-model="newGroup.cn" placeholder="Group name" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none" required />
          <input v-model="newGroup.description" placeholder="Description" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 outline-none" />
        </div>
        <div class="flex gap-3 justify-end mt-6">
          <button type="button" @click="showCreate = false" class="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button type="submit" class="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg transition-colors font-medium">Create</button>
        </div>
      </form>
    </div>

    <!-- Confirm Delete Modal -->
    <div v-if="showConfirmDelete" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-gray-900 border border-gray-800 p-6 rounded-xl w-96 shadow-2xl">
        <h2 class="text-xl font-bold mb-4 text-gray-100">Confirm Deletion</h2>
        <p class="text-gray-300 mb-6">Are you sure you want to delete {{ selectedCns.length }} selected groups? This action cannot be undone.</p>
        <div class="flex gap-3 justify-end">
          <button @click="showConfirmDelete = false" class="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors">Cancel</button>
          <button @click="executeBulkDelete" :disabled="isBulkActioning" class="bg-red-600 hover:bg-red-500 text-white px-5 py-2 rounded-lg transition-colors font-medium flex items-center gap-2 disabled:opacity-50">
            <span v-if="isBulkActioning" class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import api from '../api/client'

const groups = ref([])
const showCreate = ref(false)
const showConfirmDelete = ref(false)
const newGroup = ref({ cn: '', description: '' })
const memberInputs = reactive({})
const selectedCns = ref([])
const isBulkActioning = ref(false)

const allSelected = computed(() => {
  return groups.value.length > 0 && selectedCns.value.length === groups.value.length
})

function toggleAll(e) {
  if (e.target.checked) {
    selectedCns.value = groups.value.map(g => g.cn)
  } else {
    selectedCns.value = []
  }
}

async function fetchGroups() {
  const { data } = await api.get('/groups')
  groups.value = data
}

async function createGroup() {
  try {
    await api.post('/groups', newGroup.value)
    showCreate.value = false
    newGroup.value = { cn: '', description: '' }
    fetchGroups()
  } catch (e) {
    alert('Failed to create group: ' + (e.response?.data?.detail || e.message))
  }
}

function bulkDelete() {
  showConfirmDelete.value = true
}

async function executeBulkDelete() {
  isBulkActioning.value = true
  const results = await Promise.allSettled(
    selectedCns.value.map(currentCn => api.delete(`/entry`, { params: { dn: `cn=${currentCn},ou=groups,dc=example,dc=com` } }))
  )
  
  const failed = results.filter(r => r.status === 'rejected')
  if (failed.length > 0) {
    alert(`Completed with ${failed.length} errors. First error: ${failed[0].reason.response?.data?.detail || failed[0].reason.message}`)
  }
  
  selectedCns.value = []
  isBulkActioning.value = false
  showConfirmDelete.value = false
  fetchGroups()
}

async function addMember(cn) {
  const uid = memberInputs[cn]
  if (!uid) return
  await api.post(`/groups/${cn}/members`, { uid })
  memberInputs[cn] = ''
  fetchGroups()
}

onMounted(fetchGroups)
</script>
