import { useQuery } from "@tanstack/react-query";
import { usersApi } from "@/lib/api/endpoints";
import { formatIso, initialsOf } from "@/lib/utils";
import { useCan } from "@/stores/auth";
import { PageHeader } from "@/components/ui/states";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ErrorState, PageLoading } from "@/components/ui/states";

export default function Users() {
  const allowed = useCan("users:manage");
  const users = useQuery({ queryKey: ["users"], queryFn: usersApi.list, enabled: allowed });
  const roles = useQuery({ queryKey: ["roles"], queryFn: usersApi.roles, enabled: allowed });
  const perms = useQuery({ queryKey: ["permissions"], queryFn: usersApi.permissions, enabled: allowed });

  if (!allowed) {
    return <ErrorState title="Administrator access required" message="User and permission management is restricted to the administrator role." />;
  }

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Access & users"
        description="Directory of platform users, roles and the permissions each role can exercise."
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Users ({users.data?.length ?? 0})</CardTitle></CardHeader>
          <CardBody>
            {users.isLoading ? <PageLoading label="Loading users" /> : users.isError ? <ErrorState title="Could not load users" onRetry={() => void users.refetch()} /> : (
              <ul className="divide-y divide-ink-50">
                {users.data?.map((u) => (
                  <li key={u.id} className="flex items-center gap-3 py-2.5">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-900 text-xs font-semibold text-paper-50">
                      {initialsOf(u.full_name ?? u.username)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink-900">{u.full_name ?? u.username}</p>
                      <p className="truncate text-xs text-ink-500">{u.email ?? u.username}</p>
                    </div>
                    <div className="text-right">
                      <Badge tone="neutral" className="bg-ink-100 text-ink-700 ring-ink-200">{u.role.name}</Badge>
                      <p className="mt-0.5 text-xs text-ink-400">{u.last_login_at ? `Last login ${formatIso(u.last_login_at)}` : "Never signed in"}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader><CardTitle>Roles & permissions</CardTitle></CardHeader>
          <CardBody>
            {roles.isLoading ? <PageLoading label="Loading roles" /> : roles.isError ? <ErrorState title="Could not load roles" onRetry={() => void roles.refetch()} /> : (
              <div className="space-y-4">
                {roles.data?.map((role) => {
                  const keys = role.permissions.map((p) => p.key);
                  return (
                    <div key={role.id}>
                      <p className="text-sm font-medium text-ink-900">{role.name.replaceAll("_", " ")}</p>
                      {role.description ? <p className="text-xs text-ink-500">{role.description}</p> : null}
                      <p className="mt-1 text-xs text-ink-600">{keys.length} permissions</p>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="mt-6 border-t border-ink-100 pt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-500">All permission keys</p>
              {(perms.data ?? []).length === 0 ? (
                <p className="text-sm text-ink-500">No permission records returned.</p>
              ) : (
                <ul className="space-y-1">
                  {perms.data?.map((p) => (
                    <li key={p.id} className="flex items-center justify-between gap-2 text-xs">
                      <code className="text-ink-700">{p.key}</code>
                      <span className="text-ink-400">{p.description ?? ""}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}