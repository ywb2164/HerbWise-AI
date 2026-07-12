/* eslint-disable */
/* prettier-ignore */
// Generated route keys are retained from Soybean Admin so its tab, menu and theme systems remain intact.

import type { GeneratedRoute } from '@elegant-router/types';

export const generatedRoutes: GeneratedRoute[] = [
  {
    name: '403',
    path: '/403',
    component: 'layout.blank$view.403',
    meta: {
      title: '无权访问',
      constant: true,
      hideInMenu: true,
      i18nKey: 'route.403'
    }
  },
  {
    name: '404',
    path: '/404',
    component: 'layout.blank$view.404',
    meta: {
      title: '页面不存在',
      constant: true,
      hideInMenu: true,
      i18nKey: 'route.404'
    }
  },
  {
    name: '500',
    path: '/500',
    component: 'layout.blank$view.500',
    meta: {
      title: '系统异常',
      constant: true,
      hideInMenu: true,
      i18nKey: 'route.500'
    }
  },
  {
    name: 'about',
    path: '/about',
    component: 'layout.base$view.about',
    meta: {
      title: 'about',
      i18nKey: 'route.about'
    }
  },
  {
    name: 'alova',
    path: '/alova',
    component: 'layout.base',
    meta: {
      title: '模型与智能体',
      icon: 'carbon:machine-learning-model',
      order: 3,
      roles: ['R_ADMIN'],
      i18nKey: 'route.alova'
    },
    children: [
      {
        name: 'alova_request',
        path: '/alova/request',
        component: 'view.alova_request',
        meta: {
          title: '模型服务',
          icon: 'carbon:model-alt',
          order: 1,
          roles: ['R_ADMIN'],
          i18nKey: 'route.alova_request'
        }
      },
      {
        name: 'alova_scenes',
        path: '/alova/scenes',
        component: 'view.alova_scenes',
        meta: {
          title: '智能体编排',
          icon: 'carbon:flow',
          order: 2,
          roles: ['R_ADMIN'],
          i18nKey: 'route.alova_scenes'
        }
      }
    ]
  },
  {
    name: 'function',
    path: '/function',
    component: 'layout.base',
    meta: {
      title: '系统运维',
      icon: 'carbon:operations-record',
      order: 5,
      roles: ['R_ADMIN'],
      i18nKey: 'route.function'
    },
    children: [
      {
        name: 'function_hide-child',
        path: '/function/hide-child',
        meta: {
          title: 'function_hide-child',
          i18nKey: 'route.function_hide-child'
        },
        children: [
          {
            name: 'function_hide-child_one',
            path: '/function/hide-child/one',
            component: 'view.function_hide-child_one',
            meta: {
              title: 'function_hide-child_one',
              i18nKey: 'route.function_hide-child_one'
            }
          },
          {
            name: 'function_hide-child_three',
            path: '/function/hide-child/three',
            component: 'view.function_hide-child_three',
            meta: {
              title: 'function_hide-child_three',
              i18nKey: 'route.function_hide-child_three'
            }
          },
          {
            name: 'function_hide-child_two',
            path: '/function/hide-child/two',
            component: 'view.function_hide-child_two',
            meta: {
              title: 'function_hide-child_two',
              i18nKey: 'route.function_hide-child_two'
            }
          }
        ]
      },
      {
        name: 'function_multi-tab',
        path: '/function/multi-tab',
        component: 'view.function_multi-tab',
        meta: {
          title: 'function_multi-tab',
          i18nKey: 'route.function_multi-tab'
        }
      },
      {
        name: 'function_request',
        path: '/function/request',
        component: 'view.function_request',
        meta: {
          title: '运行日志',
          icon: 'carbon:activity',
          order: 1,
          roles: ['R_ADMIN'],
          i18nKey: 'route.function_request'
        }
      },
      {
        name: 'function_super-page',
        path: '/function/super-page',
        component: 'view.function_super-page',
        meta: {
          title: 'function_super-page',
          i18nKey: 'route.function_super-page'
        }
      },
      {
        name: 'function_tab',
        path: '/function/tab',
        component: 'view.function_tab',
        meta: {
          title: 'function_tab',
          i18nKey: 'route.function_tab'
        }
      },
      {
        name: 'function_toggle-auth',
        path: '/function/toggle-auth',
        component: 'view.function_toggle-auth',
        meta: {
          title: '系统配置',
          icon: 'carbon:settings-adjust',
          order: 2,
          roles: ['R_ADMIN'],
          i18nKey: 'route.function_toggle-auth'
        }
      }
    ]
  },
  {
    name: 'home',
    path: '/home',
    component: 'layout.base$view.home',
    meta: {
      title: '管理总览',
      icon: 'mdi:monitor-dashboard',
      order: 1,
      roles: ['R_ADMIN'],
      i18nKey: 'route.home'
    }
  },
  {
    name: 'iframe-page',
    path: '/iframe-page/:url',
    component: 'layout.base$view.iframe-page',
    props: true,
    meta: {
      title: 'iframe-page',
      i18nKey: 'route.iframe-page'
    }
  },
  {
    name: 'login',
    path: '/login/:module(pwd-login|code-login|register|reset-pwd|bind-wechat)?',
    component: 'layout.blank$view.login',
    props: true,
    meta: {
      title: '统一登录',
      constant: true,
      hideInMenu: true,
      i18nKey: 'route.login'
    }
  },
  {
    name: 'manage',
    path: '/manage',
    component: 'layout.base',
    meta: {
      title: '组织与权限',
      icon: 'carbon:user-role',
      order: 2,
      roles: ['R_ADMIN'],
      i18nKey: 'route.manage'
    },
    children: [
      {
        name: 'manage_menu',
        path: '/manage/menu',
        component: 'view.manage_menu',
        meta: {
          title: '菜单管理',
          icon: 'material-symbols:route',
          order: 3,
          roles: ['R_ADMIN'],
          i18nKey: 'route.manage_menu'
        }
      },
      {
        name: 'manage_role',
        path: '/manage/role',
        component: 'view.manage_role',
        meta: {
          title: '角色管理',
          icon: 'carbon:user-role',
          order: 2,
          roles: ['R_ADMIN'],
          i18nKey: 'route.manage_role'
        }
      },
      {
        name: 'manage_user',
        path: '/manage/user',
        component: 'view.manage_user',
        meta: {
          title: '用户管理',
          icon: 'ph:users-three',
          order: 1,
          roles: ['R_ADMIN'],
          i18nKey: 'route.manage_user'
        }
      },
      {
        name: 'manage_user-detail',
        path: '/manage/user-detail/:id',
        component: 'view.manage_user-detail',
        meta: {
          title: 'manage_user-detail',
          i18nKey: 'route.manage_user-detail'
        }
      }
    ]
  },
  {
    name: 'multi-menu',
    path: '/multi-menu',
    component: 'layout.base',
    meta: {
      title: 'multi-menu',
      i18nKey: 'route.multi-menu'
    },
    children: [
      {
        name: 'multi-menu_first',
        path: '/multi-menu/first',
        meta: {
          title: 'multi-menu_first',
          i18nKey: 'route.multi-menu_first'
        },
        children: [
          {
            name: 'multi-menu_first_child',
            path: '/multi-menu/first/child',
            component: 'view.multi-menu_first_child',
            meta: {
              title: 'multi-menu_first_child',
              i18nKey: 'route.multi-menu_first_child'
            }
          }
        ]
      },
      {
        name: 'multi-menu_second',
        path: '/multi-menu/second',
        meta: {
          title: 'multi-menu_second',
          i18nKey: 'route.multi-menu_second'
        },
        children: [
          {
            name: 'multi-menu_second_child',
            path: '/multi-menu/second/child',
            meta: {
              title: 'multi-menu_second_child',
              i18nKey: 'route.multi-menu_second_child'
            },
            children: [
              {
                name: 'multi-menu_second_child_home',
                path: '/multi-menu/second/child/home',
                component: 'view.multi-menu_second_child_home',
                meta: {
                  title: 'multi-menu_second_child_home',
                  i18nKey: 'route.multi-menu_second_child_home'
                }
              }
            ]
          }
        ]
      }
    ]
  },
  {
    name: 'plugin',
    path: '/plugin',
    component: 'layout.base',
    meta: {
      title: '内容治理',
      icon: 'carbon:document-security',
      order: 4,
      roles: ['R_ADMIN'],
      i18nKey: 'route.plugin'
    },
    children: [
      {
        name: 'plugin_barcode',
        path: '/plugin/barcode',
        component: 'view.plugin_barcode',
        meta: {
          title: 'plugin_barcode',
          i18nKey: 'route.plugin_barcode'
        }
      },
      {
        name: 'plugin_charts',
        path: '/plugin/charts',
        meta: {
          title: 'plugin_charts',
          i18nKey: 'route.plugin_charts'
        },
        children: [
          {
            name: 'plugin_charts_antv',
            path: '/plugin/charts/antv',
            component: 'view.plugin_charts_antv',
            meta: {
              title: 'plugin_charts_antv',
              i18nKey: 'route.plugin_charts_antv'
            }
          },
          {
            name: 'plugin_charts_echarts',
            path: '/plugin/charts/echarts',
            component: 'view.plugin_charts_echarts',
            meta: {
              title: 'plugin_charts_echarts',
              i18nKey: 'route.plugin_charts_echarts'
            }
          },
          {
            name: 'plugin_charts_vchart',
            path: '/plugin/charts/vchart',
            component: 'view.plugin_charts_vchart',
            meta: {
              title: 'plugin_charts_vchart',
              i18nKey: 'route.plugin_charts_vchart'
            }
          }
        ]
      },
      {
        name: 'plugin_copy',
        path: '/plugin/copy',
        component: 'view.plugin_copy',
        meta: {
          title: '提示词模板',
          icon: 'carbon:text-annotation-toggle',
          order: 1,
          roles: ['R_ADMIN'],
          i18nKey: 'route.plugin_copy'
        }
      },
      {
        name: 'plugin_editor',
        path: '/plugin/editor',
        meta: {
          title: 'plugin_editor',
          i18nKey: 'route.plugin_editor'
        },
        children: [
          {
            name: 'plugin_editor_markdown',
            path: '/plugin/editor/markdown',
            component: 'view.plugin_editor_markdown',
            meta: {
              title: 'plugin_editor_markdown',
              i18nKey: 'route.plugin_editor_markdown'
            }
          },
          {
            name: 'plugin_editor_quill',
            path: '/plugin/editor/quill',
            component: 'view.plugin_editor_quill',
            meta: {
              title: 'plugin_editor_quill',
              i18nKey: 'route.plugin_editor_quill'
            }
          }
        ]
      },
      {
        name: 'plugin_excel',
        path: '/plugin/excel',
        component: 'view.plugin_excel',
        meta: {
          title: 'plugin_excel',
          i18nKey: 'route.plugin_excel'
        }
      },
      {
        name: 'plugin_gantt',
        path: '/plugin/gantt',
        meta: {
          title: 'plugin_gantt',
          i18nKey: 'route.plugin_gantt'
        },
        children: [
          {
            name: 'plugin_gantt_dhtmlx',
            path: '/plugin/gantt/dhtmlx',
            component: 'view.plugin_gantt_dhtmlx',
            meta: {
              title: 'plugin_gantt_dhtmlx',
              i18nKey: 'route.plugin_gantt_dhtmlx'
            }
          },
          {
            name: 'plugin_gantt_vtable',
            path: '/plugin/gantt/vtable',
            component: 'view.plugin_gantt_vtable',
            meta: {
              title: 'plugin_gantt_vtable',
              i18nKey: 'route.plugin_gantt_vtable'
            }
          }
        ]
      },
      {
        name: 'plugin_icon',
        path: '/plugin/icon',
        component: 'view.plugin_icon',
        meta: {
          title: '测试用例',
          icon: 'carbon:test-tool',
          order: 2,
          roles: ['R_ADMIN'],
          i18nKey: 'route.plugin_icon'
        }
      },
      {
        name: 'plugin_map',
        path: '/plugin/map',
        component: 'view.plugin_map',
        meta: {
          title: 'plugin_map',
          i18nKey: 'route.plugin_map'
        }
      },
      {
        name: 'plugin_pdf',
        path: '/plugin/pdf',
        component: 'view.plugin_pdf',
        meta: {
          title: 'plugin_pdf',
          i18nKey: 'route.plugin_pdf'
        }
      },
      {
        name: 'plugin_pinyin',
        path: '/plugin/pinyin',
        component: 'view.plugin_pinyin',
        meta: {
          title: 'plugin_pinyin',
          i18nKey: 'route.plugin_pinyin'
        }
      },
      {
        name: 'plugin_print',
        path: '/plugin/print',
        component: 'view.plugin_print',
        meta: {
          title: 'plugin_print',
          i18nKey: 'route.plugin_print'
        }
      },
      {
        name: 'plugin_swiper',
        path: '/plugin/swiper',
        component: 'view.plugin_swiper',
        meta: {
          title: 'plugin_swiper',
          i18nKey: 'route.plugin_swiper'
        }
      },
      {
        name: 'plugin_tables',
        path: '/plugin/tables',
        meta: {
          title: 'plugin_tables',
          i18nKey: 'route.plugin_tables'
        },
        children: [
          {
            name: 'plugin_tables_vtable',
            path: '/plugin/tables/vtable',
            component: 'view.plugin_tables_vtable',
            meta: {
              title: 'plugin_tables_vtable',
              i18nKey: 'route.plugin_tables_vtable'
            }
          }
        ]
      },
      {
        name: 'plugin_typeit',
        path: '/plugin/typeit',
        component: 'view.plugin_typeit',
        meta: {
          title: 'plugin_typeit',
          i18nKey: 'route.plugin_typeit'
        }
      },
      {
        name: 'plugin_video',
        path: '/plugin/video',
        component: 'view.plugin_video',
        meta: {
          title: 'plugin_video',
          i18nKey: 'route.plugin_video'
        }
      }
    ]
  },
  {
    name: 'pro-naive',
    path: '/pro-naive',
    component: 'layout.base',
    meta: {
      title: 'pro-naive',
      i18nKey: 'route.pro-naive'
    },
    children: [
      {
        name: 'pro-naive_form',
        path: '/pro-naive/form',
        meta: {
          title: 'pro-naive_form',
          i18nKey: 'route.pro-naive_form'
        },
        children: [
          {
            name: 'pro-naive_form_basic',
            path: '/pro-naive/form/basic',
            component: 'view.pro-naive_form_basic',
            meta: {
              title: 'pro-naive_form_basic',
              i18nKey: 'route.pro-naive_form_basic'
            }
          },
          {
            name: 'pro-naive_form_query',
            path: '/pro-naive/form/query',
            component: 'view.pro-naive_form_query',
            meta: {
              title: 'pro-naive_form_query',
              i18nKey: 'route.pro-naive_form_query'
            }
          },
          {
            name: 'pro-naive_form_step',
            path: '/pro-naive/form/step',
            component: 'view.pro-naive_form_step',
            meta: {
              title: 'pro-naive_form_step',
              i18nKey: 'route.pro-naive_form_step'
            }
          }
        ]
      },
      {
        name: 'pro-naive_table',
        path: '/pro-naive/table',
        meta: {
          title: 'pro-naive_table',
          i18nKey: 'route.pro-naive_table'
        },
        children: [
          {
            name: 'pro-naive_table_remote',
            path: '/pro-naive/table/remote',
            component: 'view.pro-naive_table_remote',
            meta: {
              title: 'pro-naive_table_remote',
              i18nKey: 'route.pro-naive_table_remote'
            }
          },
          {
            name: 'pro-naive_table_row-edit',
            path: '/pro-naive/table/row-edit',
            component: 'view.pro-naive_table_row-edit',
            meta: {
              title: 'pro-naive_table_row-edit',
              i18nKey: 'route.pro-naive_table_row-edit'
            }
          }
        ]
      }
    ]
  },
  {
    name: 'user-center',
    path: '/user-center',
    component: 'layout.base$view.user-center',
    meta: {
      title: 'user-center',
      i18nKey: 'route.user-center'
    }
  }
];
