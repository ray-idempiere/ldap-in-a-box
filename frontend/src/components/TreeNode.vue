<template>
  <div class="tree-node">
    <!-- Node item row -->
    <div 
      class="flex items-center py-1 px-2 cursor-pointer hover:bg-gray-800 group relative"
      :class="{ 'bg-indigo-900/50 text-indigo-300': selectedDn === node.dn }"
      @click="toggle"
      @contextmenu.prevent="showContextMenu($event)"
    >
      <!-- Expander arrow -->
      <div class="w-5 flex justify-center text-gray-500">
        <span v-if="node.hasChildren" class="transform transition-transform text-xs" :class="{ 'rotate-90': expanded }">▶</span>
      </div>
      
      <!-- Icon -->
      <span class="mr-2 text-base">{{ icon }}</span>
      
      <!-- Label -->
      <span class="truncate" :title="node.dn">{{ node.rdn }}</span>
    </div>

    <!-- Context Menu -->
    <div v-if="contextMenu" 
         class="fixed z-50 bg-gray-800 border border-gray-600 rounded shadow-xl py-1 text-sm text-gray-200"
         :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
         @click.stop
    >
      <div class="px-4 py-1.5 hover:bg-gray-700 cursor-pointer" @click="emitAction('create')">New Entry</div>
      <div class="px-4 py-1.5 hover:bg-red-900/50 text-red-400 cursor-pointer" @click="emitAction('delete')">Delete</div>
    </div>

    <!-- Children -->
    <div v-if="expanded && node.hasChildren" class="pl-4 border-l border-gray-700 ml-4">
      <div v-if="loadingChildren" class="py-1 px-2 text-gray-500 text-xs italic">Loading...</div>
      <TreeNode 
        v-else
        v-for="child in (node.children || [])" 
        :key="child.dn" 
        :node="child" 
        :selectedDn="selectedDn"
        @select="$emit('select', $event)"
        @action="$emit('action', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../api/client'

const props = defineProps({
  node: Object,
  selectedDn: String
})

const emit = defineEmits(['select', 'action'])

const expanded = ref(false)
const loadingChildren = ref(false)
const contextMenu = ref(null)

// Initially expand root node if it's the root
onMounted(() => {
  if (props.node.children) {
    expanded.value = true
  }
  document.addEventListener('click', hideContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
})

const icon = computed(() => {
  const oc = props.node.objectClass.map(c => c.toLowerCase())
  if (oc.includes('organizationalunit') || oc.includes('organization') || oc.includes('dcobject')) return '📁'
  if (oc.includes('inetorgperson') || oc.includes('posixaccount')) return '👤'
  if (oc.includes('posixgroup') || oc.includes('groupofnames')) return '👥'
  return '📄'
})

async function toggle() {
  emit('select', props.node.dn)
  hideContextMenu()
  
  if (!props.node.hasChildren) return
  
  if (!expanded.value && !props.node.children) {
    loadingChildren.value = true
    try {
      const { data } = await api.get('/tree', { params: { base_dn: props.node.dn } })
      props.node.children = data
    } catch (e) {
      console.error(e)
    } finally {
      loadingChildren.value = false
    }
  }
  expanded.value = !expanded.value
}

function showContextMenu(e) {
  emit('select', props.node.dn)
  contextMenu.value = { x: e.clientX, y: e.clientY }
}

function hideContextMenu() {
  contextMenu.value = null
}

function emitAction(action) {
  emit('action', { action, dn: props.node.dn, node: props.node })
  hideContextMenu()
}
</script>
