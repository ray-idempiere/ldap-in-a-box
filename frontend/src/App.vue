<template>
  <div class="flex h-screen bg-gray-950 overflow-hidden font-sans">
    
    <!-- Sidebar Navigation -->
    <nav v-if="showNav" class="w-56 bg-gray-900 text-gray-300 flex flex-col border-r border-gray-800 flex-shrink-0">
      <div class="p-4 border-b border-gray-800 flex flex-col items-start justify-center gap-1">
        <div class="font-bold text-lg text-white tracking-widest uppercase">
          LDAP<span class="text-indigo-400">-in-a-Box</span>
        </div>
        <span class="text-[10px] text-gray-500 font-mono bg-gray-800/50 px-2 py-0.5 rounded">v0.2.0</span>
      </div>
      
      <div class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <router-link to="/tree" class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-800 hover:text-white transition-colors text-sm" active-class="bg-indigo-900/50 text-indigo-300 ring-1 ring-indigo-800">
          <span class="text-lg">🌳</span> <span class="font-medium">{{ $t('nav.treeBrowser') }}</span>
        </router-link>
        
        <div class="pt-4 pb-2 px-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ $t('nav.shortcuts') }}</div>
        
        <router-link to="/" class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm" active-class="bg-gray-800 text-white">
          <span class="text-base">📊</span> {{ $t('nav.dashboard') }}
        </router-link>
        <router-link to="/users" class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm" active-class="bg-gray-800 text-white">
          <span class="text-base">👥</span> {{ $t('nav.users') }}
        </router-link>
        <router-link to="/groups" class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors text-sm" active-class="bg-gray-800 text-white">
          <span class="text-base">📁</span> {{ $t('nav.groups') }}
        </router-link>
      </div>
      
      <div class="p-3 border-t border-gray-800 space-y-2">
        <select v-model="$i18n.locale" @change="changeLanguage($event)" class="w-full bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer">
          <option value="en">English (US)</option>
          <option value="zh-TW">繁體中文 (TW)</option>
        </select>
        
        <button @click="logout" class="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-red-900/50 hover:text-red-300 text-gray-400 px-4 py-2 rounded-lg transition-colors text-sm">
          🚪 {{ $t('nav.logout') }}
        </button>
      </div>
    </nav>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-auto bg-gray-950 flex flex-col relative w-full">
      <div class="flex-1 relative" :class="{ 'p-6 max-w-7xl mx-auto w-full': route.path !== '/tree' }">
        <router-view />
      </div>
    </main>
    
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const route = useRoute()
const { locale } = useI18n()
const showNav = computed(() => route.path !== '/login')

function changeLanguage(event) {
  const newLocale = event.target.value
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>
