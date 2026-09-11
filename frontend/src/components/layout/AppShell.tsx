import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  Database,
  FileText,
  FileUp,
  FlaskConical,
  Gavel,
  LayoutDashboard,
  LogOut,
  Network,
  Radar,
  Search,
  ShieldCheck,
  Users2,
} from "lucide-react";
import { cn, initialsOf } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { useLogoutMutation } from "@/lib/api/queries";
import { DROP_PERMISSIONS } from "@/lib/nav";
import { Badge } from "@/components/ui/badge";
import { Dropdown, DropdownItem } from "@/components/ui/dropdown";

interface NavEntry {
  to: string;
  label: string;
  icon: React.ReactNode;
  permission?: string;
  matchPaths?: string[];
}

const NAV: NavEntry[] = [
  { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="h-4 w-4" />, matchPaths: ["/dashboard"] },
  {
    to: "/intelligence",
    label: "Intelligence",
    icon: <Search className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.intelligenceRead,
    matchPaths: ["/intelligence"],
  },
  {
    to: "/alerts",
    label: "Alerts",
    icon: <Bell className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.alertsRead,
    matchPaths: ["/alerts", "/alert",
    ],
  },
  {
    to: "/athletes",
    label: "Athletes",
    icon: <Users2 className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.athletesRead,
    matchPaths: ["/athletes"],
  },
  {
    to: "/investigations",
    label: "Investigations",
    icon: <Gavel className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.investigationsRead,
    matchPaths: ["/investigations"],
  },
  {
    to: "/relationships",
    label: "Relationships",
    icon: <Network className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.athletesRead,
    matchPaths: ["/relationships"],
  },
  {
    to: "/reports",
    label: "Reports",
    icon: <FileText className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.reportsRead,
    matchPaths: ["/reports"],
  },
  {
    to: "/imports",
    label: "Data import",
    icon: <FileUp className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.importsRead,
    matchPaths: ["/imports"],
  },
  {
    to: "/osint",
    label: "Open source",
    icon: <Radar className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.osintRead,
    matchPaths: ["/osint"],
  },
  {
    to: "/ai",
    label: "AI Assistant",
    icon: <FlaskConical className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.investigationsRead,
    matchPaths: ["/ai"],
  },
  {
    to: "/audit",
    label: "Audit log",
    icon: <ShieldCheck className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.auditRead,
    matchPaths: ["/audit"],
  },
  {
    to: "/users",
    label: "Access & users",
    icon: <ShieldCheck className="h-4 w-4" />,
    permission: DROP_PERMISSIONS.usersManage,
    matchPaths: ["/users"],
  },
];

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const logout = useLogoutMutation();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  const visible = NAV.filter((n) => !n.permission || hasPermission(n.permission));

  const handleLogout = () => {
    logout.mutate(undefined, {
      onSettled: () => {
        void navigate("/login", { replace: true });
      },
    });
  };

  return (
    <div className="min-h-screen bg-paper-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-ink-950 focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-paper-50"
      >
        Skip to content
      </a>
      <div className="flex min-h-screen">
        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-ink-100 bg-ink-950 text-paper-100 transition-transform",
            "lg:static lg:translate-x-0",
            open ? "translate-x-0" : "-translate-x-full",
          )}
        >
          <div className="flex h-16 items-center gap-2.5 border-b border-ink-800 px-5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-signal-600 text-sm font-bold text-white">
              V
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-wide text-white">VERITY</p>
              <p className="text-[11px] text-ink-400">Anti-Doping Intelligence</p>
            </div>
          </div>

          <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Main navigation">
            {visible.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-ink-800 text-white"
                      : "text-ink-300 hover:bg-ink-900 hover:text-paper-50",
                  )
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-ink-800 p-3">
            <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-700 text-xs font-semibold text-paper-50">
                {initialsOf(user?.full_name ?? user?.username)}
              </div>
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-sm font-medium text-paper-50">{user?.full_name ?? user?.username}</p>
                <p className="truncate text-xs text-ink-400">{user?.role?.name?.replaceAll("_", " ")}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="mt-2 flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-ink-300 transition-colors hover:bg-ink-900 hover:text-paper-50"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col lg:pl-0">
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-ink-100 bg-paper-50/90 px-4 backdrop-blur lg:px-6">
            <button
              className="rounded-md p-2 text-ink-600 hover:bg-ink-100 lg:hidden"
              onClick={() => setOpen((o) => !o)}
              aria-label="Toggle navigation"
            >
              <NavGlyph />
            </button>
            <div className="hidden items-center gap-2 text-sm text-ink-500 lg:flex">
              <Database className="h-4 w-4 text-ink-400" />
              <span>
                {user?.role?.permissions?.length ? (
                  <Badge tone="neutral" className="bg-ink-100 text-ink-600 ring-ink-200">
                    {visible.length} modules available
                  </Badge>
                ) : (
                  "Workspace"
                )}
              </span>
            </div>
            <UserMenu userFullName={user?.full_name ?? user?.username} role={user?.role?.name} onLogout={handleLogout} />
          </header>

          <main id="main" className="min-w-0 flex-1 px-4 py-6 lg:px-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

function NavGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function UserMenu({ userFullName, role, onLogout }: { userFullName: string | undefined; role?: string; onLogout: () => void }) {
  return (
    <Dropdown
      trigger={
        <button
          className="flex items-center gap-2.5 rounded-md px-2 py-1.5 transition-colors hover:bg-ink-100"
          aria-label="Account menu"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-900 text-xs font-semibold text-paper-50">
            {initialsOf(userFullName)}
          </div>
          <span className="hidden text-sm font-medium text-ink-800 sm:inline">{userFullName}</span>
        </button>
      }
    >
      <div className="px-2.5 py-1.5">
        <p className="text-sm font-medium text-ink-900">{userFullName}</p>
        <p className="text-xs text-ink-500">{role?.replaceAll("_", " ")}</p>
      </div>
      <div className="my-1 h-px bg-ink-100" />
      <DropdownItem onSelect={onLogout}>Sign out</DropdownItem>
    </Dropdown>
  );
}