<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">{{ $t('users.title') }}</h1>
      <button @click="showCreate = true" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">+ {{ $t('users.newUser') }}</button>
    </div>
    <!-- Search and Bulk Actions -->
    <div class="flex items-center gap-3 mb-4">
      <input v-model="search" @input="fetchUsers" :placeholder="$t('users.search')" class="flex-1 bg-gray-900 border border-gray-800 text-gray-200 rounded-lg px-4 py-2 focus:ring-1 focus:ring-indigo-500 focus:outline-none" />
      
      <transition name="fade">
        <div v-if="selectedUids.length > 0" class="flex items-center gap-3 bg-indigo-900/30 border border-indigo-800/50 rounded-lg px-4 py-2">
          <span class="text-indigo-300 text-sm font-medium">{{ $t('users.selected', { count: selectedUids.length }) }}</span>
          <div class="h-4 w-px bg-indigo-800 mx-1"></div>
          <button @click="bulkDelete" :disabled="isBulkActioning" class="text-sm bg-red-900/50 text-red-300 hover:bg-red-800/80 px-3 py-1 rounded transition-colors disabled:opacity-50 flex items-center gap-1">
            <span v-if="isBulkActioning" class="animate-spin inline-block w-3 h-3 border-2 border-red-300 border-t-transparent rounded-full"></span>
            🗑 {{ $t('users.delete') }}
          </button>
          <button @click="selectedUids = []" class="text-sm text-gray-400 hover:text-gray-200 px-2 py-1">{{ $t('users.cancel') }}</button>
        </div>
      </transition>
    </div>

    <div class="bg-gray-900 rounded-xl shadow border border-gray-800 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-800/50 text-gray-400"><tr>
          <th class="text-left px-4 py-3 w-10">
            <input type="checkbox" :checked="allSelected" @change="toggleAll" class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-900" />
          </th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.uid') }}</th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.name') }}</th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.email') }}</th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.vpn') }}</th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.mailMonitor') }}</th>
          <th class="text-left px-4 py-3 font-medium">{{ $t('users.status') }}</th>
        </tr></thead>
        <tbody class="divide-y divide-gray-800">
          <tr v-for="u in users" :key="u.uid" class="hover:bg-gray-800/50 transition-colors group cursor-pointer" @click="toggleSelectionOrGo(u.uid, $event)">
            <td class="px-4 py-3" @click.stop>
              <input type="checkbox" :value="u.uid" v-model="selectedUids" class="rounded border-gray-600 bg-gray-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-gray-900" />
            </td>
            <td class="px-4 py-3 p-0">
              <span class="font-mono text-indigo-400 group-hover:underline">{{ u.uid }}</span>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ u.cn }}</td>
            <td class="px-4 py-3 text-gray-500">{{ u.mail }}</td>
            <td class="px-4 py-3">
              <span :class="u.is_vpn === 'Y' ? 'text-green-400' : 'text-gray-600'">{{ u.is_vpn === 'Y' ? '✓' : '—' }}</span>
            </td>
            <td class="px-4 py-3">
              <span :class="u.is_mail_monitor === 'Y' ? 'text-yellow-400' : 'text-gray-600'">{{ u.is_mail_monitor === 'Y' ? '✓' : '—' }}</span>
            </td>
            <td class="px-4 py-3">
              <span :class="u.enabled ? 'text-green-400' : 'text-red-400'">{{ u.enabled ? 'Active' : 'Disabled' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <form @submit.prevent="createUser" class="bg-gray-900 border border-gray-800 p-6 rounded-xl w-96 shadow-2xl">
        <h2 class="text-xl font-bold mb-5 text-gray-100">New User</h2>
        <div class="space-y-3">
          <input v-model="form.uid" placeholder="Username (uid)" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none" required />
          <input v-model="form.cn" placeholder="Full Name" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none" required />
          <input v-model="form.sn" placeholder="Surname" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none" required />
          <input v-model="form.mail" placeholder="Email" type="email" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
          <input v-model="form.password" placeholder="Password" type="password" class="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-gray-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none" required />
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
        <p class="text-gray-300 mb-6">Are you sure you want to delete {{ selectedUids.length }} selected users? This action cannot be undone.</p>
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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'

const router = useRouter()
const users = ref([])
const search = ref('')
const showCreate = ref(false)
const showConfirmDelete = ref(false)
const form = ref({ uid: '', cn: '', sn: '', mail: '', password: '' })
const selectedUids = ref([])
const isBulkActioning = ref(false)

const allSelected = computed(() => {
  return users.value.length > 0 && selectedUids.value.length === users.value.length
})

function toggleAll(e) {
  if (e.target.checked) {
    selectedUids.value = users.value.map(u => u.uid)
  } else {
    selectedUids.value = []
  }
}

function toggleSelectionOrGo(uid, event) {
  // If user is holding Ctrl/Cmd, toggle selection
  if (event.ctrlKey || event.metaKey) {
    if (selectedUids.value.includes(uid)) {
      selectedUids.value = selectedUids.value.filter(id => id !== uid)
    } else {
      selectedUids.value.push(uid)
    }
  } else {
    // Normal click = navigate
    router.push(`/users/${uid}`)
  }
}

async function fetchUsers() {
  const { data } = await api.get('/users', { params: { search: search.value } })
  users.value = data
  // Clean up selected root if users disappear from search
  selectedUids.value = selectedUids.value.filter(uid => data.some(u => u.uid === uid))
}

async function createUser() {
  try {
    await api.post('/users', form.value)
    showCreate.value = false
    form.value = { uid: '', cn: '', sn: '', mail: '', password: '' }
    fetchUsers()
  } catch (e) {
    alert('Failed to create user: ' + (e.response?.data?.detail || e.message))
  }
}

function bulkDelete() {
  showConfirmDelete.value = true
}

async function executeBulkDelete() {
  isBulkActioning.value = true
  const results = await Promise.allSettled(
    selectedUids.value.map(uid => api.delete(`/users/${uid}`))
  )
  
  const failed = results.filter(r => r.status === 'rejected')
  if (failed.length > 0) {
    alert(`Completed with ${failed.length} errors. First error: ${failed[0].reason.response?.data?.detail || failed[0].reason.message}`)
  }
  
  selectedUids.value = []
  isBulkActioning.value = false
  showConfirmDelete.value = false
  fetchUsers()
}

onMounted(fetchUsers)
</script>
