<template>
  <div class="flex items-center justify-center min-h-[80vh]">
    <form @submit.prevent="handleReset" class="bg-white p-8 rounded-lg shadow-md w-96">
      <h1 class="text-2xl font-bold mb-6 text-center">Password Reset</h1>
      <div v-if="message" :class="success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" class="p-3 rounded mb-4">{{ message }}</div>
      <input v-model="username" placeholder="Username" class="w-full border rounded px-3 py-2 mb-3" required />
      <input v-model="currentPassword" type="password" placeholder="Current Password" class="w-full border rounded px-3 py-2 mb-3" required />
      <input v-model="newPassword" type="password" placeholder="New Password" class="w-full border rounded px-3 py-2 mb-4" required />
      <button type="submit" class="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700">Reset Password</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api/client'

const username = ref('')
const currentPassword = ref('')
const newPassword = ref('')
const message = ref('')
const success = ref(false)

async function handleReset() {
  try {
    // First authenticate with current password
    const { data } = await api.post('/auth/login', {
      username: username.value,
      password: currentPassword.value,
    })
    // Use the token to reset password
    await api.put(`/users/${username.value}/password`, {
      new_password: newPassword.value,
    }, { headers: { Authorization: `Bearer ${data.access_token}` } })
    success.value = true
    message.value = 'Password changed successfully!'
  } catch {
    success.value = false
    message.value = 'Failed. Check your current password.'
  }
}
</script>
