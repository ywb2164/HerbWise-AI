import type { ElegantConstRoute, ElegantRoute } from '@elegant-router/types';
import { generatedRoutes } from '../elegant/routes';
import { layouts, views } from '../elegant/imports';
import { transformElegantRoutesToVueRoutes } from '../elegant/transform';

const herbwiseRouteNames = new Set([
  '403',
  '404',
  '500',
  'login',
  'home',
  'manage',
  'manage_user',
  'manage_role',
  'manage_menu',
  'alova',
  'alova_request',
  'alova_scenes',
  'plugin',
  'plugin_copy',
  'plugin_icon',
  'function',
  'function_request',
  'function_toggle-auth'
]);

export function createStaticRoutes() {
  const constantRoutes: ElegantRoute[] = [];
  const authRoutes: ElegantRoute[] = [];

  generatedRoutes.forEach(item => {
    if (!herbwiseRouteNames.has(item.name)) return;

    let route: ElegantRoute = item;
    if ('children' in item && item.children) {
      route = {
        ...item,
        children: item.children.filter(child => herbwiseRouteNames.has(child.name))
      } as ElegantRoute;
    }

    if (route.meta?.constant) constantRoutes.push(route);
    else authRoutes.push(route);
  });

  return { constantRoutes, authRoutes };
}

export function getAuthVueRoutes(routes: ElegantConstRoute[]) {
  const herbwiseViews: typeof views = {
    ...views,
    login: () => import('@/herbwise/views/AdminEntryView.vue'),
    home: () => import('@/herbwise/views/admin/AdminOverviewView.vue'),
    manage_user: () => import('@/herbwise/views/admin/AdminUsersView.vue'),
    manage_role: () => import('@/herbwise/views/admin/AdminRolesView.vue'),
    manage_menu: () => import('@/herbwise/views/admin/AdminMenusView.vue'),
    alova_request: () => import('@/herbwise/views/admin/AdminModelsView.vue'),
    alova_scenes: () => import('@/herbwise/views/admin/AdminAgentsView.vue'),
    plugin_copy: () => import('@/herbwise/views/admin/AdminPromptsView.vue'),
    plugin_icon: () => import('@/herbwise/views/admin/AdminTestsView.vue'),
    function_request: () => import('@/herbwise/views/admin/AdminOperationsView.vue'),
    'function_toggle-auth': () => import('@/herbwise/views/admin/AdminSystemView.vue')
  };

  return transformElegantRoutesToVueRoutes(routes, layouts, herbwiseViews);
}
