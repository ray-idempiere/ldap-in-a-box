<template>
  <div v-if="user">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold">{{ user.cn }} ({{ user.uid }})</h1>
      <div class="flex gap-3">
        <button @click="disableUser" class="bg-yellow-500 text-white px-4 py-2 rounded">Disable</button>
        <button @click="deleteUser" class="bg-red-600 text-white px-4 py-2 rounded">Delete</button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <form @submit.prevent="saveUser" class="bg-white p-6 rounded-lg shadow">
        <h2 class="text-lg font-bold mb-4">Profile</h2>
        <label class="block text-sm font-medium mb-1">Full Name</label>
        <input v-model="form.cn" class="w-full border rounded px-3 py-2 mb-3" />
        <label class="block text-sm font-medium mb-1">Surname</label>
        <input v-model="form.sn" class="w-full border rounded px-3 py-2 mb-3" />
        <label class="block text-sm font-medium mb-1">Email</label>
        <input v-model="form.mail" type="email" class="w-full border rounded px-3 py-2 mb-3" />
        <label class="block text-sm font-medium mb-1">VPN Access</label>
        <select v-model="form.is_vpn" class="w-full border rounded px-3 py-2 mb-4">
          <option value="Y">Yes</option>
          <option value="N">No</option>
        </select>
        <label class="block text-sm font-medium mb-1">Mail Monitor</label>
        <select v-model="form.is_mail_monitor" class="w-full border rounded px-3 py-2 mb-4">
          <option value="Y">Yes</option>
          <option value="N">No</option>
        </select>
        <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded">Save</button>
      </form>

      <div class="space-y-6">
        <form @submit.prevent="resetPassword" class="bg-white p-6 rounded-lg shadow">
          <h2 class="text-lg font-bold mb-4">Reset Password</h2>
          <input v-model="newPassword" type="password" placeholder="New password" class="w-full border rounded px-3 py-2 mb-3" required />
          <button type="submit" class="bg-orange-500 text-white px-4 py-2 rounded">Reset</button>
        </form>

        <div class="bg-white p-6 rounded-lg shadow">
          <h2 class="text-lg font-bold mb-4">Groups</h2>
          <div v-for="g in user.groups" :key="g" class="inline-block bg-gray-200 rounded px-3 py-1 mr-2 mb-2">{{ g }}</div>
          <p v-if="!user.groups.length" class="text-gray-400">No groups</p>
        </div>
      </div>
    </div>

    <!-- Toast container -->
    <div v-if="toast" class="fixed bottom-6 right-6 z-50 px-5 py-3 rounded-lg shadow-lg text-sm font-medium transition-all"
      :class="toast.type === 'success' ? 'bg-green-900 text-green-200 border border-green-700' : 'bg-red-900 text-red-200 border border-red-700'">
      {{ toast.message }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'

const route = useRoute()
const router = useRouter()
const user = ref(null)
const form = ref({})
const newPassword = ref('')
const toast = ref(null)

function showToast(type, message) {
  toast.value = { type, message }
  setTimeout(() => { toast.value = null }, 3000)
}

async function fetchUser() {
  const { data } = await api.get(`/users/${route.params.uid}`)
  user.value = data
  form.value = { cn: data.cn, sn: data.sn, mail: data.mail, is_vpn: data.is_vpn, is_mail_monitor: data.is_mail_monitor }
}

async function saveUser() {
  try {
    await api.put(`/users/${route.params.uid}`, form.value)
    fetchUser()
    showToast('success', '✅ User updated successfully')
  } catch (e) {
    showToast('error', '❌ Failed to update user: ' + (e.response?.data?.detail || e.message))
  }
}

async function resetPassword() {
  await api.put(`/users/${route.params.uid}/password`, { new_password: newPassword.value })
  newPassword.value = ''
  showToast('success', '✅ Password reset successfully')
}

async function disableUser() {
  if (confirm('Disable this user?')) {
    await api.post(`/users/${route.params.uid}/disable`)
    fetchUser()
  }
}

async function deleteUser() {
  if (confirm('Delete this user permanently?')) {
    await api.delete(`/users/${route.params.uid}`)
    router.push('/users')
  }
}

onMounted(fetchUser)
</script>
