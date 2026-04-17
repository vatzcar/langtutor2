export const ALL_PERMISSIONS = [
  'languages.view', 'languages.add', 'languages.edit', 'languages.delete',
  'personas.view', 'personas.add', 'personas.edit', 'personas.delete',
  'users.view', 'users.add', 'users.edit', 'users.delete',
  'admins.view', 'admins.add', 'admins.edit', 'admins.delete',
  'plans.manage', 'reports.view', 'logs.view',
] as const;

export type Permission = (typeof ALL_PERMISSIONS)[number];

export interface PermissionGroup {
  key: string;
  label: string;
  granular: boolean;
  actions: string[];
}

export const PERMISSION_GROUPS: PermissionGroup[] = [
  { key: 'languages', label: 'Languages', granular: true, actions: ['view', 'add', 'edit', 'delete'] },
  { key: 'personas', label: 'Personas', granular: true, actions: ['view', 'add', 'edit', 'delete'] },
  { key: 'users', label: 'Users', granular: true, actions: ['view', 'add', 'edit', 'delete'] },
  { key: 'admins', label: 'Admins', granular: true, actions: ['view', 'add', 'edit', 'delete'] },
  { key: 'plans', label: 'Plans', granular: false, actions: ['manage'] },
  { key: 'reports', label: 'Reports', granular: false, actions: ['view'] },
  { key: 'logs', label: 'Logs', granular: false, actions: ['view'] },
];

export function isSuperAdmin(perms: string[]): boolean {
  return ALL_PERMISSIONS.every((p) => perms.includes(p));
}

// Which permission controls visibility of each sidebar menu item.
export const MENU_VISIBILITY_PERMISSION: Record<string, string> = {
  '/users': 'users.view',
  '/languages': 'languages.view',
  '/personas': 'personas.view',
  '/plans': 'plans.manage',
  '/reports': 'reports.view',
};

// For the /users route we accept EITHER users.view OR admins.view.
export function canSeeRoute(route: string, perms: string[]): boolean {
  if (route === '/users') {
    return perms.includes('users.view') || perms.includes('admins.view');
  }
  const required = MENU_VISIBILITY_PERMISSION[route];
  if (!required) return true;
  return perms.includes(required);
}
