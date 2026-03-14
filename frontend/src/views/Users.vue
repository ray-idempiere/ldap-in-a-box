<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">Users</h1>
      <button @click="showCreate = true" class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">+ New User</button>
    </div>
    <input v-model="search" @input="fetchUsers" placeholder="Search users..." class="w-full border rounded px-3 py-2 mb-4" />
    <div class="bg-white rounded-lg shadow overflow-hidden">
      <table class="w-full">
        <thead class="bg-gray-50"><tr>
          <th class="text-left px-4 py-3">UID</th>
          <th class="text-left px-4 py-3">Name</th>
          <th class="text-left px-4 py-3">Email</th>
          <th class="text-left px-4 py-3">VPN</th>
          <th class="text-left px-4 py-3">Status</th>
        </tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.uid" @click="$router.push(`/users/${u.uid}`)" class="hover:bg-gray-50 cursor-pointer border-t">
            <td class="px-4 py-3">{{ u.uid }}</td>
            <td class="px-4 py-3">{{ u.cn }}</td>
            <td class="px-4 py-3">{{ u.mail }}</td>
            <td class="px-4 py-3">{{ u.is_vpn }}</td>
            <td class="px-4 py-3">
              <span :class="u.enabled ? 'text-green-600' : 'text-red-600'">{{ u.enabled ? 'Active' : 'Disabled' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center">
      <form @submit.prevent="createUser" class="bg-white p-6 rounded-lg w-96">
        <h2 class="text-xl font-bold mb-4">New User</h2>
        <input v-model="form.uid" placeholder="Username (uid)" class="w-full border rounded px-3 py-2 mb-3" required />
        <input v-model="form.cn" placeholder="Full Name" class="w-full border rounded px-3 py-2 mb-3" required />
        <input v-model="form.sn" placeholder="Surname" class="w-full border rounded px-3 py-2 mb-3" required />
        <input v-model="form.mail" placeholder="Email" type="email" class="w-full border rounded px-3 py-2 mb-3" />
        <input v-model="form.password" placeholder="Password" type="password" class="w-full border rounded px-3 py-2 mb-3" required />
        <div class="flex gap-3">
          <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded">Create</button>
          <button type="button" @click="showCreate = false" class="border px-4 py-2 rounded">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const users = ref([])
const search = ref('')
const showCreate = ref(false)
const form = ref({ uid: '', cn: '', sn: '', mail: '', password: '' })

async function fetchUsers() {
  const { data } = await api.get('/users', { params: { search: search.value } })
  users.value = data
}

async function createUser() {
  await api.post('/users', form.value)
  showCreate.value = false
  form.value = { uid: '', cn: '', sn: '', mail: '', password: '' }
  fetchUsers()
}

onMounted(fetchUsers)
</script>
