<template>
  <div class="flex h-screen bg-gray-100 overflow-hidden font-sans">
    
    <!-- Sidebar Navigation -->
    <nav v-if="showNav" class="w-64 bg-gray-900 text-gray-300 flex flex-col border-r border-gray-800">
      <div class="p-6 font-bold text-xl text-white tracking-widest uppercase border-b border-gray-800">
        LDAP<span class="text-indigo-400">-in-a-Box</span>
      </div>
      
      <div class="flex-1 px-4 py-6 space-y-2 overflow-y-auto">
        <router-link to="/tree" class="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-gray-800 hover:text-white transition-colors" active-class="bg-gray-800 text-white ring-1 ring-gray-700">
          <span class="text-xl">🌳</span> <span class="font-medium">Tree Browser</span>
        </router-link>
        
        <div class="pt-6 pb-2 px-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">Shortcuts</div>
        
        <router-link to="/" class="flex items-center gap-3 px-4 py-2 rounded border border-transparent hover:border-gray-700 hover:bg-gray-800 transition-colors" active-class="bg-gray-800 text-white">
          <span class="text-lg">📊</span> Dashboard
        </router-link>
        <router-link to="/users" class="flex items-center gap-3 px-4 py-2 rounded border border-transparent hover:border-gray-700 hover:bg-gray-800 transition-colors" active-class="bg-gray-800 text-white">
          <span class="text-lg">👥</span> Users
        </router-link>
        <router-link to="/groups" class="flex items-center gap-3 px-4 py-2 rounded border border-transparent hover:border-gray-700 hover:bg-gray-800 transition-colors" active-class="bg-gray-800 text-white">
          <span class="text-lg">📁</span> Groups
        </router-link>
      </div>
      
      <div class="p-4 border-t border-gray-800">
        <button @click="logout" class="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-red-900 hover:text-red-100 text-gray-300 px-4 py-2 rounded transition-colors">
          <span class="text-lg">🚪</span> Logout
        </button>
      </div>
    </nav>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-auto bg-white flex flex-col relative w-full">
      <div class="flex-1 relative" :class="{ 'p-6 max-w-7xl mx-auto w-full': route.path !== '/tree' }">
        <router-view />
      </div>
    </main>
    
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const showNav = computed(() => route.path !== '/login')

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>
