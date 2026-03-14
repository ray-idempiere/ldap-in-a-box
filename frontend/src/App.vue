<template>
  <div class="min-h-screen bg-gray-100">
    <nav v-if="isLoggedIn" class="bg-indigo-600 text-white p-4">
      <div class="max-w-7xl mx-auto flex items-center gap-6">
        <span class="font-bold text-lg">LDAP-in-a-Box</span>
        <router-link to="/" class="hover:underline">Dashboard</router-link>
        <router-link to="/users" class="hover:underline">Users</router-link>
        <router-link to="/groups" class="hover:underline">Groups</router-link>
        <button @click="logout" class="ml-auto hover:underline">Logout</button>
      </div>
    </nav>
    <main class="max-w-7xl mx-auto p-6">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isLoggedIn = computed(() => !!localStorage.getItem('token'))

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>
