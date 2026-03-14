<template>
  <div class="tree-node" :draggable="isDraggable" @dragstart="onDragStart" @dragover.prevent="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
    <!-- Node item row -->
    <div 
      class="flex items-center py-1 px-2 cursor-pointer hover:bg-gray-800 group relative transition-colors"
      :class="{ 
        'bg-indigo-900/50 text-indigo-300': selectedDn === node.dn,
        'bg-indigo-800/30 ring-1 ring-indigo-500': dragOver
      }"
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
      <span class="truncate flex-1" :class="{ 'opacity-50': searchQuery && !matchesSearch }" :title="node.dn">
        <template v-if="searchQuery && matchesSearch">
          <span v-html="highlightedLabel"></span>
        </template>
        <template v-else>{{ node.rdn }}</template>
      </span>

      <!-- Child count badge -->
      <span v-if="node.hasChildren && node.children" class="text-xs text-gray-600 ml-1">{{ node.children.length }}</span>
    </div>

    <!-- Context Menu -->
    <div v-if="contextMenu" 
         class="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg shadow-xl py-1 text-sm text-gray-200 min-w-[180px]"
         :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
         @click.stop
    >
      <div class="px-4 py-2 hover:bg-gray-700 cursor-pointer flex items-center gap-2" @click="emitAction('create')">
        <span>✚</span> New Child Entry
      </div>
      <div class="px-4 py-2 hover:bg-gray-700 cursor-pointer flex items-center gap-2" @click="copyDn">
        <span>📋</span> Copy DN
      </div>
      <div class="h-px bg-gray-700 my-1"></div>
      <div class="px-4 py-2 hover:bg-red-900/50 text-red-400 cursor-pointer flex items-center gap-2" @click="emitAction('delete')">
        <span>🗑</span> Delete
      </div>
    </div>

    <!-- Children -->
    <div v-if="expanded && node.hasChildren" class="pl-4 border-l border-gray-700/50 ml-4">
      <div v-if="loadingChildren" class="py-1 px-2 text-gray-500 text-xs italic flex items-center gap-2">
        <span class="animate-spin">⟳</span> Loading...
      </div>
      <TreeNode 
        v-else
        v-for="child in filteredChildren" 
        :key="child.dn" 
        :node="child" 
        :selectedDn="selectedDn"
        :searchQuery="searchQuery"
        @select="$emit('select', $event)"
        @action="$emit('action', $event)"
        @move="$emit('move', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { apiV2 as api } from '../api/client'

const props = defineProps({
  node: Object,
  selectedDn: String,
  searchQuery: { type: String, default: '' }
})

const emit = defineEmits(['select', 'action', 'move'])

const expanded = ref(false)
const loadingChildren = ref(false)
const contextMenu = ref(null)
const dragOver = ref(false)

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
  if (oc.includes('posixgroup') || oc.includes('groupofnames') || oc.includes('groupofuniquenames')) return '👥'
  if (props.node.rdn.startsWith('cn=admin') || oc.includes('simpleSecurityObject')) return '🔧'
  return '📄'
})

const isDraggable = computed(() => {
  const oc = props.node.objectClass.map(c => c.toLowerCase())
  return !oc.includes('dcobject') && !oc.includes('organization')
})

const matchesSearch = computed(() => {
  if (!props.searchQuery) return true
  return props.node.rdn.toLowerCase().includes(props.searchQuery.toLowerCase()) || 
         props.node.dn.toLowerCase().includes(props.searchQuery.toLowerCase())
})

const highlightedLabel = computed(() => {
  if (!props.searchQuery) return props.node.rdn
  const re = new RegExp(`(${props.searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return props.node.rdn.replace(re, '<span class="bg-yellow-500/40 text-yellow-200 rounded px-0.5">$1</span>')
})

const filteredChildren = computed(() => {
  if (!props.node.children) return []
  if (!props.searchQuery) return props.node.children
  return props.node.children.filter(child => subtreeMatches(child, props.searchQuery))
})

function subtreeMatches(node, query) {
  const q = query.toLowerCase()
  if (node.rdn.toLowerCase().includes(q) || node.dn.toLowerCase().includes(q)) return true
  if (node.children) return node.children.some(c => subtreeMatches(c, q))
  return node.hasChildren // keep expandable nodes
}

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

// Auto-expand when searching
if (props.searchQuery && props.node.hasChildren && !props.node.children) {
  // will be expanded by parent's filter logic
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

function copyDn() {
  navigator.clipboard.writeText(props.node.dn)
  hideContextMenu()
}

// Drag & Drop
function onDragStart(e) {
  e.dataTransfer.setData('text/plain', props.node.dn)
  e.dataTransfer.effectAllowed = 'move'
}

function onDragOver(e) {
  const oc = props.node.objectClass.map(c => c.toLowerCase())
  if (oc.includes('organizationalunit') || oc.includes('organization') || oc.includes('dcobject')) {
    e.dataTransfer.dropEffect = 'move'
    dragOver.value = true
  }
}

function onDragLeave() {
  dragOver.value = false
}

function onDrop(e) {
  dragOver.value = false
  const sourceDn = e.dataTransfer.getData('text/plain')
  if (sourceDn && sourceDn !== props.node.dn) {
    emit('move', { sourceDn, targetDn: props.node.dn })
  }
}
</script>
