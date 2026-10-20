import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ChatView from '../views/ChatView.vue'
import KnowledgeView from '../views/KnowledgeView.vue'
import KnowledgeDetailView from '../views/KnowledgeDetailView.vue'
import DocumentView from '../views/DocumentView.vue'
import UserAdminView from '../views/UserAdminView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true } },
    { path: '/register', component: RegisterView, meta: { public: true } },
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', redirect: '/chat' },
        { path: 'chat', component: ChatView },
        { path: 'knowledge', component: KnowledgeView },
        { path: 'knowledge/:id', component: KnowledgeDetailView },
        { path: 'documents/:id', component: DocumentView },
        { path: 'admin/users', component: UserAdminView },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const token = localStorage.getItem('docflow_token')
  if (!to.meta.public && !token) return '/login'
  if (to.meta.public && token) return '/chat'
})

export default router
