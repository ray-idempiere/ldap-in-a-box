<template>
  <div class="text-gray-200">
    <h1 class="text-2xl font-bold mb-8 text-gray-100">📊 Dashboard</h1>
    
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
      <div class="bg-gray-900 border border-gray-800 p-5 rounded-xl">
        <div class="text-3xl font-bold text-indigo-400">{{ stats.users }}</div>
        <div class="text-gray-500 text-sm mt-1">Users</div>
      </div>
      <div class="bg-gray-900 border border-gray-800 p-5 rounded-xl">
        <div class="text-3xl font-bold text-green-400">{{ stats.groups }}</div>
        <div class="text-gray-500 text-sm mt-1">Groups</div>
      </div>
      <div class="bg-gray-900 border border-gray-800 p-5 rounded-xl">
        <div class="text-3xl font-bold text-blue-400">{{ stats.vpnUsers }}</div>
        <div class="text-gray-500 text-sm mt-1">VPN Users</div>
      </div>
      <div class="bg-gray-900 border border-gray-800 p-5 rounded-xl">
        <div class="text-3xl font-bold text-emerald-400">{{ stats.ous }}</div>
        <div class="text-gray-500 text-sm mt-1">Org Units</div>
      </div>
    </div>

    <!-- Server Info -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">🖥 Server Status</h2>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">LDAP Connection</span>
            <span :class="serverOk ? 'text-green-400' : 'text-red-400'">{{ serverOk ? '● Online' : '● Offline' }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">Base DN</span>
            <span class="text-gray-300 font-mono text-xs">{{ baseDn }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">API Version</span>
            <span class="text-gray-300">v1 + v2</span>
          </div>
        </div>
      </div>

      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">📋 Quick Actions</h2>
        <div class="space-y-2">
          <router-link to="/tree" class="block w-full text-left bg-gray-800 hover:bg-gray-700 px-4 py-2.5 rounded-lg text-sm transition-colors">
            🌳 Open Tree Browser
          </router-link>
          <button @click="exportBackup" :disabled="exporting" class="w-full text-left bg-gray-800 hover:bg-gray-700 px-4 py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50">
            💾 {{ exporting ? 'Exporting...' : 'Export LDIF Backup' }}
          </button>
          
          <input type="file" ref="fileInput" class="hidden" accept=".ldif" @change="handleFileUpload" />
          <button @click="triggerFileInput" :disabled="importing" class="w-full text-left bg-gray-800 hover:bg-gray-700 px-4 py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50">
            📥 {{ importing ? 'Importing...' : 'Import LDIF Restore' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Recent Users Table -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">👤 Users</h2>
      <div v-if="recentUsers.length === 0" class="text-gray-600 text-sm italic">No users found</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500 border-b border-gray-800">
            <th class="pb-2 font-medium">UID</th>
            <th class="pb-2 font-medium">Name</th>
            <th class="pb-2 font-medium">Email</th>
            <th class="pb-2 font-medium">VPN</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-800/50">
          <tr v-for="u in recentUsers" :key="u.uid" class="hover:bg-gray-800/50">
            <td class="py-2 font-mono text-indigo-300">{{ u.uid }}</td>
            <td class="py-2 text-gray-300">{{ u.cn }}</td>
            <td class="py-2 text-gray-500">{{ u.mail || '—' }}</td>
            <td class="py-2"><span :class="u.is_vpn === 'Y' ? 'text-green-400' : 'text-gray-600'">{{ u.is_vpn === 'Y' ? '✓' : '—' }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { apiV2 } from '../api/client'

const stats = ref({ users: 0, groups: 0, vpnUsers: 0, ous: 0 })
const serverOk = ref(false)
const baseDn = ref('')
const recentUsers = ref([])
const exporting = ref(false)
const importing = ref(false)
const fileInput = ref(null)

onMounted(async () => {
  try {
    const [usersRes, groupsRes] = await Promise.all([
      api.get('/users'),
      api.get('/groups'),
    ])
    const users = usersRes.data
    recentUsers.value = users.slice(0, 10)
    
    // Try to get tree root for OU count
    let ous = 0
    try {
      const { data: root } = await apiV2.get('/tree/root')
      baseDn.value = root.dn
      if (root.children) {
        ous = root.children.filter(c => c.objectClass.map(o => o.toLowerCase()).includes('organizationalunit')).length
      }
      serverOk.value = true
    } catch (_) {
      serverOk.value = false
    }

    stats.value = {
      users: users.length,
      groups: groupsRes.data.length,
      vpnUsers: users.filter(u => u.is_vpn === 'Y').length,
      ous
    }
  } catch (e) {
    console.error(e)
  }
})

async function exportBackup() {
  exporting.value = true
  try {
    const { data } = await api.post('/backup')
    const blob = new Blob([data.ldif || JSON.stringify(data)], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ldap-backup-${new Date().toISOString().slice(0,10)}.ldif`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('Backup failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    exporting.value = false
  }
}

function triggerFileInput() {
  fileInput.value.click()
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  importing.value = true
  const formData = new FormData()
  formData.append('file', file)

  try {
    await api.post('/backup/restore', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    alert('Restore completed successfully! Some existing entries may have been skipped.')
    // Refresh stats
    const [usersRes, groupsRes] = await Promise.all([
      api.get('/users'),
      api.get('/groups'),
    ])
    stats.value.users = usersRes.data.length
    stats.value.groups = groupsRes.data.length
    stats.value.vpnUsers = usersRes.data.filter(u => u.is_vpn === 'Y').length
  } catch (e) {
    alert('Restore failed: ' + (e.response?.data?.detail || e.message))
  } finally {
    importing.value = false
    event.target.value = '' // Reset input
  }
}
</script>
