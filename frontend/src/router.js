import { createRouter, createWebHistory } from 'vue-router'

const routes = [
    { path: '/login', component: () => import('./views/Login.vue') },
    { path: '/', component: () => import('./views/Dashboard.vue'), meta: { auth: true } },
    { path: '/tree', component: () => import('./views/TreeBrowser.vue'), meta: { auth: true } },
    { path: '/users', component: () => import('./views/Users.vue'), meta: { auth: true } },
    { path: '/users/:uid', component: () => import('./views/UserDetail.vue'), meta: { auth: true } },
    { path: '/groups', component: () => import('./views/Groups.vue'), meta: { auth: true } },
    { path: '/password-reset', component: () => import('./views/PasswordReset.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
    if (to.meta.auth && !localStorage.getItem('token')) {
        return '/login'
    }
})

export default router
