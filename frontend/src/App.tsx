import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  BarChart3,
  BookOpen,
  Building2,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  CalendarClock,
  Download,
  FlaskConical,
  GraduationCap,
  LayoutDashboard,
  KeyRound,
  LogOut,
  Menu,
  Pencil,
  Play,
  Printer,
  RefreshCw,
  School,
  Settings,
  ShieldCheck,
  Trash2,
  Users,
  X,
} from "lucide-react";
import {
  addLabBatchOfferings,
  addOffering,
  academicTerms,
  activateAcademicTerm,
  applyReschedule,
  bootstrapAdmin,
  bootstrapStatus,
  changePassword,
  create,
  deleteTimetable,
  createTermCohorts,
  downloadDatabase,
  restoreDatabase,
  list,
  login,
  registerAccount,
  registrationOptions,
  loadDemoData,
  offerings,
  previewReschedule,
  remove,
  removeOffering,
  request,
  RescheduleRequest,
  rescheduleHistory,
  semesters,
  Session,
  setupCreate,
  setupOptions,
  setupRemove,
  setupRemoveRoot,
  SetupStatus,
  setupStatus,
  setupUpdate,
  setupUpdateRoot,
  facultyAvailability,
  roomAvailability,
  saveRoomAvailability,
  saveFacultyAvailability,
  setTimetableStatus,
  timetableBackup,
  timetableBackups,
  timetable,
  timetableValidation,
  timetableHistory,
  update,
  updateOffering,
  User,
  validateSetup,
} from "./api";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
function storedUser(): User | null {
  try {
    return JSON.parse(localStorage.getItem("timetable_user") || "null");
  } catch {
    return null;
  }
}
function saveSession(
  data: { access_token: string; user: User },
  onLogin: (u: User) => void,
) {
  localStorage.setItem("timetable_token", data.access_token);
  localStorage.setItem("timetable_user", JSON.stringify(data.user));
  onLogin(data.user);
}
function errorText(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
function splitCapabilities(value: string) {
  const seen = new Set<string>();
  return value
    .split(/[,;\n]+/)
    .map((item) => item.trim().replace(/\s+/g, " "))
    .filter((item) => {
      const key = item.toLocaleLowerCase();
      if (!item || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}
function formatIndiaDateTime(value: string) {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  return `${new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Kolkata",
  }).format(new Date(normalized))} IST`;
}

export default function App() {
  const [user, setUser] = useState<User | null>(storedUser);
  useEffect(() => {
    const clearExpiredSession = () => setUser(null);
    window.addEventListener("timetable:unauthorized", clearExpiredSession);
    return () => window.removeEventListener("timetable:unauthorized", clearExpiredSession);
  }, []);
  const bootstrap = useQuery({
    queryKey: ["bootstrap"],
    queryFn: bootstrapStatus,
    retry: false,
    enabled: !user,
  });
  if (!user && bootstrap.isLoading)
    return <main className="loading-page">Opening timetable system…</main>;
  if (!user && bootstrap.data?.needs_admin)
    return <FirstAdmin onLogin={setUser} hasDepartmentData={Boolean(bootstrap.data.has_department_data)} />;
  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" /> : <Login onLogin={setUser} />}
      />
      <Route
        path="/*"
        element={
          user ? (
            <Shell
              user={user}
              logout={() => {
                localStorage.clear();
                setUser(null);
              }}
            />
          ) : (
            <Navigate to="/login" />
          )
        }
      />
    </Routes>
  );
}

function FirstAdmin({ onLogin, hasDepartmentData }: { onLogin: (u: User) => void; hasDepartmentData: boolean }) {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const mutation = useMutation({
    mutationFn: () => bootstrapAdmin(form),
    onSuccess: (data) => saveSession(data, onLogin),
  });
  return (
    <AuthLayout
      eyebrow="SGSITS · Department handover"
      title="Create the department administrator"
      text={hasDepartmentData
        ? "The department's starter records are ready. Create a private administrator account, then review and complete only the missing data."
        : "Create the first administrator account, then enter or import the department's academic records."}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <h2>Administrator account</h2>
        <label>
          Full name
          <input
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </label>
        <label>
          Email
          <input
            required
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>
        <label>
          Password
          <input
            required
            minLength={8}
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        {mutation.error && (
          <div className="error">{errorText(mutation.error)}</div>
        )}
        <button className="primary" disabled={mutation.isPending}>
          {mutation.isPending ? "Creating…" : "Create admin & continue"}
          <ChevronRight size={18} />
        </button>
      </form>
    </AuthLayout>
  );
}
function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState("");
  const [role, setRole] = useState<User["role"] | null>(null);
  const [creating, setCreating] = useState(false);
  const mutation = useMutation({
    mutationFn: () => login(email, password, role!),
    onSuccess: (d) => saveSession(d, onLogin),
  });
  const roleChoices: Array<{ role: User["role"]; label: string; detail: string; icon: React.ReactNode }> = [
    { role: "admin", label: "Administrator", detail: "Manage data, generate, validate and publish", icon: <ShieldCheck /> },
    { role: "faculty", label: "Faculty", detail: "View and download the faculty timetable", icon: <Users /> },
    { role: "student", label: "Student", detail: "View and download the published timetable", icon: <GraduationCap /> },
  ];
  return (
    <AuthLayout
      eyebrow="SGSITS · Electrical Engineering"
      title="Academic timetable planning for the department."
      text="Choose your workspace to view, prepare or manage the official departmental timetable."
    >
      {!role ? <div className="role-login">
        <p className="eyebrow">Welcome</p>
        <h2>Who are you?</h2>
        <div className="role-chooser">
          {roleChoices.map((choice) => <button type="button" className="role-card" key={choice.role} onClick={() => { mutation.reset(); setRole(choice.role); }}>
            <span>{choice.icon}</span>
            <div><strong>{choice.label}</strong><small>{choice.detail}</small></div>
            <ChevronRight size={18} />
          </button>)}
        </div>
      </div> : creating ? <RegisterAccount role={role} onLogin={onLogin} onBack={() => setCreating(false)} /> : <form
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <button type="button" className="role-back" onClick={() => { mutation.reset(); setRole(null); }}>← Change workspace</button>
        <p className="eyebrow">{role} workspace</p>
        <h2>Sign in to continue</h2>
        <label>
          Email
          <input
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
          />
        </label>
        <label>
          Password
          <input
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
          />
        </label>
        {mutation.error && (
          <div className="error">{errorText(mutation.error)}</div>
        )}
        <button className="primary" disabled={mutation.isPending}>
          {mutation.isPending ? "Signing in…" : "Sign in"}
          <ChevronRight size={18} />
        </button>
        <button type="button" className="auth-switch" onClick={() => { mutation.reset(); setCreating(true); }}>
          New {role}? Create your own account
        </button>
      </form>}
    </AuthLayout>
  );
}

function RegisterAccount({ role, onLogin, onBack }: { role: User["role"]; onLogin: (u: User) => void; onBack: () => void }) {
  const options = useQuery({ queryKey: ["registration-options"], queryFn: registrationOptions });
  const [form, setForm] = useState({ name: "", email: "", password: "", confirm: "", faculty_id: "", academic_year_id: "", semester: "", student_group_id: "" });
  const [facultySearch, setFacultySearch] = useState("");
  const [message, setMessage] = useState("");
  const years = options.data?.academic_years || [];
  const year = years.find((item) => String(item.id) === form.academic_year_id);
  const semestersForYear = year?.semesters || [];
  const semester = semestersForYear.find((item) => String(item.semester_number) === form.semester);
  const faculty = (options.data?.faculty || []).filter((item) => `${item.name} ${item.faculty_code}`.toLowerCase().includes(facultySearch.toLowerCase()));
  const mutation = useMutation({
    mutationFn: () => {
      if (form.password !== form.confirm) throw new Error("Passwords do not match");
      return registerAccount({
        name: form.name,
        email: form.email,
        password: form.password,
        role,
        faculty_id: role === "faculty" ? Number(form.faculty_id) : null,
        academic_year_id: role === "student" ? Number(form.academic_year_id) : null,
        student_group_id: role === "student" ? form.student_group_id : null,
      });
    },
    onSuccess: (data) => {
      if (data.access_token && data.user) saveSession({ access_token: data.access_token, user: data.user }, onLogin);
      else setMessage(data.message || "Account request submitted.");
    },
  });
  if (message) return <div><button type="button" className="role-back" onClick={onBack}>← Back to sign in</button><h2>Request received</h2><div className="success">{message}</div></div>;
  return <form onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }}>
    <button type="button" className="role-back" onClick={onBack}>← Back to sign in</button>
    <p className="eyebrow">{role} registration</p>
    <h2>Create your account</h2>
    {role === "faculty" && <>
      <label>Search your name or faculty code<input value={facultySearch} onChange={(event) => setFacultySearch(event.target.value)} placeholder="Start typing…" /></label>
      <label>Select your faculty record<select required value={form.faculty_id} onChange={(event) => setForm({ ...form, faculty_id: event.target.value })}><option value="">Choose yourself</option>{faculty.map((item) => <option key={item.id} value={item.id}>{item.faculty_code} · {item.name}</option>)}</select></label>
      <p className="registration-note">Use the exact SGSITS email already stored against your faculty record.</p>
    </>}
    {role === "student" && <>
      <label>Academic year<select required value={form.academic_year_id} onChange={(event) => setForm({ ...form, academic_year_id: event.target.value, semester: "", student_group_id: "" })}><option value="">Choose academic year</option>{years.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.term_type} semester</option>)}</select></label>
      <label>Semester<select required value={form.semester} disabled={!year} onChange={(event) => setForm({ ...form, semester: event.target.value, student_group_id: "" })}><option value="">Choose semester</option>{semestersForYear.map((item) => <option key={item.semester_number} value={item.semester_number}>Semester {item.semester_number}</option>)}</select></label>
      <label>Batch / group<select required value={form.student_group_id} disabled={!semester} onChange={(event) => setForm({ ...form, student_group_id: event.target.value })}><option value="">Choose batch</option>{semester?.groups.map((group) => <option key={group} value={group}>{group}</option>)}</select></label>
    </>}
    {role === "admin" && <p className="registration-note">For security, an existing administrator must approve additional administrator accounts.</p>}
    <label>Full name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
    <label>SGSITS email<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="name@sgsits.ac.in" /></label>
    <label>Create password<input required minLength={8} type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>
    <label>Confirm password<input required minLength={8} type="password" value={form.confirm} onChange={(event) => setForm({ ...form, confirm: event.target.value })} /></label>
    {options.error && <div className="error">{errorText(options.error)}</div>}
    {mutation.error && <div className="error">{errorText(mutation.error)}</div>}
    <button className="primary" disabled={mutation.isPending || options.isLoading}>{mutation.isPending ? "Creating…" : "Create account"}<ChevronRight size={18} /></button>
  </form>;
}
function AuthLayout({
  eyebrow,
  title,
  text,
  children,
}: {
  eyebrow: string;
  title: string;
  text: string;
  children: React.ReactNode;
}) {
  return (
    <main className="login-page">
      <section className="login-brand">
        <div className="brand-mark">
          <img src="/sgsits-logo.png" alt="SGSITS Indore emblem" />
        </div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{text}</p>
        <div className="trust">
          <ShieldCheck />
          <span>Every generated schedule is independently validated.</span>
        </div>
        <div className="institute-signature">
          <strong>Shri G. S. Institute of Technology &amp; Science</strong>
          <span>Govt. Aided Autonomous Institute · Indore · Estd. 1952</span>
        </div>
      </section>
      <section className="login-panel">{children}</section>
    </main>
  );
}

const adminNav = [
  ["Dashboard", "/", LayoutDashboard],
  ["Start Setup", "/prepare", BookOpen],
  ["Faculty", "/faculty", Users],
  ["Teacher Availability", "/availability", CalendarClock],
  ["Rooms & Labs", "/rooms", Building2],
  ["Reservations", "/reservations", Clock3],
  ["User Access", "/users", ShieldCheck],
  ["Generate", "/generate", Play],
  ["Reschedule", "/reschedule", RefreshCw],
  ["Timetable", "/timetable", CalendarDays],
  ["Analytics", "/analytics", BarChart3],
  ["My Account", "/account", KeyRound],
] as const;
const studentNav = [
  ["My Timetable", "/timetable", CalendarDays],
  ["Faculty Directory", "/faculty", Users],
  ["Rooms & Labs", "/rooms", Building2],
  ["Download", "/download", Download],
  ["My Account", "/account", KeyRound],
] as const;
const facultyNav = [
  ["My Timetable", "/timetable", CalendarDays],
  ["Faculty Directory", "/faculty", Users],
  ["Rooms & Labs", "/rooms", Building2],
  ["Download", "/download", Download],
  ["My Account", "/account", KeyRound],
] as const;
function Shell({ user, logout }: { user: User; logout: () => void }) {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const status = useQuery({
    queryKey: ["setup-status"],
    queryFn: setupStatus,
    enabled: user.role === "admin",
  });
  const terms = useQuery({ queryKey: ["academic-terms"], queryFn: academicTerms, enabled: user.role === "admin" });
  const activateTerm = useMutation({
    mutationFn: activateAcademicTerm,
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["setup-status"] }),
        qc.invalidateQueries({ queryKey: ["setup-options"] }),
        qc.invalidateQueries({ queryKey: ["semesters"] }),
        qc.invalidateQueries({ queryKey: ["timetable"] }),
        qc.invalidateQueries({ queryKey: ["timetable-history"] }),
      ]);
    },
  });
  const nav = user.role === "admin" ? adminNav : user.role === "faculty" ? facultyNav : studentNav;
  return (
    <div className="app-shell">
      <aside className={open ? "open" : ""}>
        <div className="logo">
          <img src="/sgsits-logo.png" alt="SGSITS Indore emblem" />
          <span>
            <strong>SGSITS</strong><small>Timetable System</small>
          </span>
          <button className="close" onClick={() => setOpen(false)}>
            <X />
          </button>
        </div>
        <nav>
          {nav.map(([label, to, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="avatar">
            {user.name
              .split(" ")
              .map((x) => x[0])
              .slice(0, 2)
              .join("")}
          </div>
          <div>
            <strong>{user.name}</strong>
            <span>{user.role}</span>
          </div>
          <button onClick={logout} title="Sign out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main className="content">
        <header>
          <button className="menu" onClick={() => setOpen(true)}>
            <Menu />
          </button>
          <div>
            {user.role === "admin" && terms.data?.items.length ? <select className="term-switcher" value={status.data?.active_year?.id || ""} onChange={(event) => activateTerm.mutate(Number(event.target.value))}>
              {terms.data.items.map((term: any) => <option value={term.id} key={term.id}>{term.name} · {term.term_type.toUpperCase()}</option>)}
            </select> : <span className="term">{status.data?.active_year?.name || `${user.role} view`}</span>}
            {user.role === "admin" ? <span className={status.data?.ready_for_validation ? "status-dot" : "status-dot pending"}>
              {status.data?.ready_for_validation ? "Ready to validate" : "Setup in progress"}
            </span> : <span className="status-dot">Read-only timetable access</span>}
          </div>
        </header>
        <Routes>
          <Route index element={<Dashboard user={user} />} />
          <Route path="prepare" element={user.role === "admin" ? <Preparation /> : <Navigate to="/" />} />
          <Route path="generate" element={user.role === "admin" ? <Generate /> : <Navigate to="/" />} />
          <Route path="reschedule" element={user.role === "admin" ? <ReschedulePage /> : <Navigate to="/" />} />
          <Route path="timetable" element={<TimetablePage user={user} />} />
          <Route path="download" element={<DownloadPage />} />
          <Route
            path="faculty"
            element={<MasterList resource="faculty" title="Faculty" user={user} />}
          />
          <Route path="availability" element={user.role === "admin" ? <AvailabilityPage user={user} /> : <Navigate to="/" />} />
          <Route
            path="rooms"
            element={
              <MasterList resource="rooms" title="Rooms & Laboratories" user={user} />
            }
          />
          <Route
            path="reservations"
            element={user.role === "admin" ?
              <MasterList resource="reservations" title="Fixed Reservations" user={user} />
            : <Navigate to="/" />}
          />
          <Route path="users" element={user.role === "admin" ? <MasterList resource="users" title="User Access" user={user} /> : <Navigate to="/" />} />
          <Route path="analytics" element={user.role === "admin" ? <Analytics /> : <Navigate to="/" />} />
          <Route path="account" element={<AccountPage user={user} />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

function PageTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </div>
  );
}
function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
function Dashboard({ user }: { user: User }) {
  const [downloadError, setDownloadError] = useState("");
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const restore = useMutation({
    mutationFn: (file: File) => restoreDatabase(file),
    onSuccess: (result) => {
      window.alert(`${result.message}\nAutomatic rollback copy: ${result.rollback_backup}`);
      localStorage.clear();
      window.location.href = "/login";
    },
  });
  const status = useQuery({
    queryKey: ["setup-status"],
    queryFn: setupStatus,
    enabled: user.role === "admin",
  });
  const runs = useQuery({
    queryKey: ["analytics"],
    queryFn: () => request<any>("/analytics/summary"),
    enabled: user.role === "admin",
  });
  if (user.role !== "admin")
    return (
      <section className="page">
        <PageTitle
          eyebrow={`${user.role} workspace`}
          title={`Welcome, ${user.name}`}
        />
        <div className="hero-card">
          <div>
            <h2>{user.role === "faculty" ? "Your teaching timetable" : "Your weekly class timetable"}</h2>
            <p>{user.role === "faculty" ? "View or print your faculty-specific schedule. Ask the timetable administrator to record any availability change." : "View and print your semester schedule. Student accounts cannot modify department data."}</p>
            <NavLink className="primary button-link" to="/timetable">
              Open timetable
            </NavLink>
          </div>
          <CalendarDays size={90} />
        </div>
      </section>
    );
  const s = status.data;
  return (
    <section className="page">
      <PageTitle
        eyebrow="SGSITS · Electrical Engineering"
        title="Department timetable administration"
      >
        <div className="actions">
          <button className="secondary" onClick={async () => { try { setDownloadError(""); await downloadDatabase("backup"); } catch (error) { setDownloadError(errorText(error)); } }}><Download size={17} /> Private backup</button>
          <button className="secondary" onClick={async () => { try { setDownloadError(""); await downloadDatabase("starter"); } catch (error) { setDownloadError(errorText(error)); } }}><School size={17} /> Starter database</button>
          <NavLink className="primary button-link" to="/prepare">
            Continue setup
            <ChevronRight size={18} />
          </NavLink>
        </div>
      </PageTitle>
      {downloadError && <div className="error">{downloadError}</div>}
      <p className="lead">
        Start with editable dummy data for a quick department presentation, or
        enter the institution's real records manually before generation.
      </p>
      <div className="metric-grid">
        <Metric
          label="Semesters"
          value={String(s?.counts.semesters ?? 0)}
          detail={`${s?.active_year?.term_type === "even" ? "2, 4, 6" : "3, 5, 7"} required`}
          icon={<GraduationCap />}
        />
        <Metric
          label="Faculty"
          value={String(s?.counts.faculty ?? 0)}
          detail="Added by admin"
          icon={<Users />}
        />
        <Metric
          label="Rooms & labs"
          value={String(s?.counts.rooms ?? 0)}
          detail="Added by admin"
          icon={<Building2 />}
        />
        <Metric
          label="Successful runs"
          value={String(runs.data?.successful_runs ?? 0)}
          detail="Generated schedules"
          icon={<ShieldCheck />}
        />
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>Preparation checklist</h3>
          {s?.steps.map((step, i) => (
            <div className="progress-row" key={step.key}>
              <span className={`step ${step.complete ? "done" : ""}`}>
                {step.complete ? <Check size={16} /> : i + 1}
              </span>
              <div>
                <strong>{step.label}</strong>
                <small>
                  {step.complete ? "Complete" : "Required before generation"}
                </small>
              </div>
              {step.complete && <ShieldCheck size={18} />}
            </div>
          ))}
          {s?.readiness_issues?.length ? <div className="readiness-issues">
            <strong>Generation blockers</strong>
            {s.readiness_issues.slice(0, 5).map((issue, index) => <small key={`${issue.code}-${index}`}>{issue.message}</small>)}
          </div> : null}
        </div>
        <div className={`card ${s?.ready_for_validation ? "accent" : ""}`}>
          <p className="eyebrow">Next action</p>
          <h2>
            {s?.ready_for_validation
              ? "Cross-check and generate"
              : "Continue entering records"}
          </h2>
          <p>
            {s?.ready_for_validation
              ? "All required categories contain data. The validator will now check capacities, assignments and conflicts."
              : "Follow the setup order so later forms can use the earlier records in dropdown menus."}
          </p>
          <NavLink
            className="primary button-link"
            to={s?.ready_for_validation ? "/generate" : "/prepare"}
          >
            {s?.ready_for_validation ? "Go to generation" : "Open setup"}
          </NavLink>
        </div>
      </div>
      <div className="card data-protection">
        <div>
          <p className="eyebrow">Data protection</p>
          <h3>Restore a private database backup</h3>
          <p className="muted">Only a verified full backup containing an active administrator is accepted. Before restoration, the system automatically saves the current database in the server's backups folder.</p>
        </div>
        <input type="file" accept=".db,.sqlite,.sqlite3" onChange={(event) => setRestoreFile(event.target.files?.[0] || null)} />
        <button className="secondary" disabled={!restoreFile || restore.isPending} onClick={() => {
          if (restoreFile && window.confirm("Restore this private backup? The current database will first be saved as a rollback copy, then replaced.")) restore.mutate(restoreFile);
        }}>{restore.isPending ? "Restoring…" : "Restore backup"}</button>
        {restore.error && <div className="error">{errorText(restore.error)}</div>}
      </div>
    </section>
  );
}

function Preparation() {
  const qc = useQueryClient();
  const [demoTerm, setDemoTerm] = useState<"odd" | "even">("odd");
  const statusQ = useQuery({
    queryKey: ["setup-status"],
    queryFn: setupStatus,
  });
  const optionsQ = useQuery({
    queryKey: ["setup-options"],
    queryFn: setupOptions,
  });
  const yearId = statusQ.data?.active_year?.id;
  const semQ = useQuery({
    queryKey: ["semesters", yearId],
    queryFn: () => semesters(yearId!),
    enabled: !!yearId,
  });
  const [selected, setSelected] = useState<number | null>(null);
  const current = selected ?? semQ.data?.items[0]?.id;
  const currentSemester = semQ.data?.items.find((x) => x.id === current);
  const coursesQ = useQuery({
    queryKey: ["offerings", current],
    queryFn: () => offerings(current!),
    enabled: !!current,
  });
  const [addingSubject, setAddingSubject] = useState(false);
  const [editingSubject, setEditingSubject] = useState<any | null>(null);
  const [addingSemester, setAddingSemester] = useState(false);
  const [editingSemester, setEditingSemester] = useState<any | null>(null);
  const [foundationEdit, setFoundationEdit] = useState<any | null>(null);
  const [editingWeek, setEditingWeek] = useState(false);
  const ids = (semQ.data?.items || []).map((x) => x.id);
  const validation = useMutation({
    mutationFn: () => validateSetup(yearId!, ids),
  });
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["setup-status"] });
    qc.invalidateQueries({ queryKey: ["setup-options"] });
    qc.invalidateQueries({ queryKey: ["semesters"] });
    qc.invalidateQueries({ queryKey: ["academic-terms"] });
  };
  const demo = useMutation({
    mutationFn: () => loadDemoData(demoTerm),
    onSuccess: refresh,
  });
  const createCohorts = useMutation({
    mutationFn: () => createTermCohorts({ academic_year_id: yearId!, department_id: optionsQ.data.departments[0].id, default_strength: 60 }),
    onSuccess: refresh,
  });
  const setupIsEmpty = !!statusQ.data && ["institutes", "departments", "academic_years", "time_slots", "faculty", "rooms", "semesters"].every((key) => !statusQ.data!.counts[key]);
  const deleteSemester = useMutation({
    mutationFn: (id: number) => setupRemove("semesters", id),
    onSuccess: () => {
      setSelected(null);
      refresh();
    },
  });
  const deleteSubject = useMutation({
    mutationFn: (id: number) => removeOffering(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["offerings", current] });
      qc.invalidateQueries({ queryKey: ["setup-status"] });
    },
  });
  const deleteFoundation = useMutation({
    mutationFn: ({ resource, id }: { resource: string; id: number }) => setupRemove(resource, id),
    onSuccess: refresh,
  });
  const deleteWeek = useMutation({ mutationFn: () => setupRemoveRoot("working-week"), onSuccess: refresh });
  const confirmDeleteSemester = () => {
    if (
      currentSemester &&
      window.confirm(
        `Delete Semester ${roman(currentSemester.semester_number)} and all its subjects?`,
      )
    )
      deleteSemester.mutate(currentSemester.id);
  };
  const confirmDeleteSubject = (subject: any) => {
    if (window.confirm(`Delete ${subject.code} - ${subject.name}?`))
      deleteSubject.mutate(subject.id);
  };
  return (
    <section className="page">
      <PageTitle eyebrow="Admin data entry" title="Start from the beginning">
        {yearId && (
          <button
            className="secondary"
            onClick={() => validation.mutate()}
            disabled={validation.isPending}
          >
            {validation.isPending ? "Checking…" : "Cross-check configuration"}
            <ShieldCheck size={17} />
          </button>
        )}
      </PageTitle>
      <p className="lead">
        Enter data in this order. Semester and subject records can be edited or
        removed before generation.
      </p>
      {setupIsEmpty && (
        <div className="card demo-starter">
          <div>
            <p className="eyebrow">Presentation shortcut</p>
            <h2>Load editable dummy data</h2>
            <p>Creates faculty, rooms, the selected three semesters, three parallel electives, a co-taught subject, sample teacher availability, and a fixed first-year electrical-lab reservation.</p>
          </div>
          <label>
            Academic term
            <select value={demoTerm} onChange={(event) => setDemoTerm(event.target.value as "odd" | "even")}>
              <option value="odd">Odd · Semesters 3, 5, 7</option>
              <option value="even">Even · Semesters 2, 4, 6</option>
            </select>
          </label>
          <button className="primary" disabled={demo.isPending} onClick={() => demo.mutate()}>
            {demo.isPending ? "Loading…" : "Load dummy setup"}
          </button>
          {demo.error && <div className="error">{errorText(demo.error)}</div>}
        </div>
      )}
      <SetupChecklist status={statusQ.data} />
      <div className="setup-section">
        <h2>1. Academic foundation</h2>
        <div className="setup-cards">
          {!statusQ.data?.counts.institutes ? (
            <QuickForm
              title="Institute"
              fields={[["name", "Institute name"]]}
              submit={(data) => setupCreate("institutes", data)}
              done={refresh}
            />
          ) : (
            <CompleteCard title="Institute" onEdit={() => setFoundationEdit({ resource: "institutes", item: optionsQ.data?.institutes[0], fields: [["name", "Institute name"]] })} onDelete={() => window.confirm("Delete the institute record?") && deleteFoundation.mutate({resource:"institutes",id:optionsQ.data?.institutes[0].id})} />
          )}
          <QuickForm
            title="Department"
            fields={[
              ["code", "Department code"],
              ["name", "Department name"],
            ]}
            submit={(data) => setupCreate("departments", data)}
            done={refresh}
          />
          {!statusQ.data?.counts.academic_years ? (
            <QuickForm
              title="Academic year"
              fields={[["name", "Example: 2026-27 Odd"], ["term_type", "Academic term", "term"]]}
              submit={(data) => setupCreate("academic-years", data)}
              done={refresh}
            />
          ) : (
            <CompleteCard title={`${statusQ.data.active_year?.name} · ${statusQ.data.active_year?.term_type?.toUpperCase()} term`} onEdit={() => setFoundationEdit({ resource: "academic-years", item: statusQ.data?.active_year, fields: [["name", "Academic year"], ["term_type", "Academic term", "term"]] })} onDelete={() => window.confirm("Delete this academic year?") && deleteFoundation.mutate({resource:"academic-years",id:statusQ.data!.active_year!.id})} />
          )}{" "}
          {!!statusQ.data?.counts.academic_years && <QuickForm title="Add another term" fields={[["name", "Example: 2026-27 Even"], ["term_type", "Academic term", "term"]]} submit={(data) => setupCreate("academic-years", data)} done={refresh} />}
          {!statusQ.data?.counts.time_slots ? (
            <WorkingWeekForm done={refresh} />
          ) : (
            <CompleteCard title="Working days & periods" onEdit={() => setEditingWeek(true)} onDelete={() => window.confirm("Delete the working week configuration?") && deleteWeek.mutate()} />
          )}
        </div>
        {!!optionsQ.data?.departments.length && <div className="foundation-list"><h3>Departments</h3>{optionsQ.data.departments.map((department: any) => <div key={department.id}><span><strong>{department.code}</strong> · {department.name}</span><div className="record-actions"><button className="icon-button" onClick={() => setFoundationEdit({ resource: "departments", item: department, fields: [["code", "Department code"], ["name", "Department name"]] })}><Pencil size={15}/></button><button className="icon-button danger" onClick={() => window.confirm(`Delete ${department.name}?`) && deleteFoundation.mutate({resource:"departments",id:department.id})}><Trash2 size={15}/></button></div></div>)}</div>}
      </div>
      <div className="setup-section">
        <div className="card-head">
          <div>
            <h2>2. Semester cohorts and subjects</h2>
            <p className="muted">
              First add faculty and rooms from the side menu. Then create
              the three combined cohorts for the active Odd or Even term. Add
              as many elective alternatives as required using the same elective group.
            </p>
          </div>
          <button
            className="primary"
            disabled={
              !yearId ||
              !optionsQ.data?.departments.length ||
              !optionsQ.data?.rooms.some(
                (r: any) => r.room_type === "theory",
              ) ||
              ids.length >= 3
            }
            onClick={() => setAddingSemester(true)}
          >
            Add semester
          </button>
          {!ids.length && yearId && !!optionsQ.data?.departments.length && (
            <button className="secondary" disabled={createCohorts.isPending} onClick={() => createCohorts.mutate()}>
              {createCohorts.isPending ? "Creating…" : `Create ${statusQ.data?.active_year?.term_type === "even" ? "II, IV, VI" : "III, V, VII"} automatically`}
            </button>
          )}
        </div>
        {ids.length === 0 ? (
          <EmptyState text="No semesters yet. Add faculty and theory rooms, then create the first semester." />
        ) : (
          <>
            <div className="semester-tabs">
              {semQ.data?.items.map((s) => (
                <button
                  className={current === s.id ? "active" : ""}
                  onClick={() => setSelected(s.id)}
                  key={s.id}
                >
                  <span>Semester {roman(s.semester_number)}</span>
                  <small>
                    {s.strength} students ·{" "}
                    {roomName(optionsQ.data, s.home_room_id)}
                  </small>
                </button>
              ))}
            </div>
            <div className="card">
              <div className="card-head">
                <div>
                  <p className="eyebrow">
                    Semester{" "}
                    {roman(
                      semQ.data?.items.find((x) => x.id === current)
                        ?.semester_number || 0,
                    )}
                  </p>
                  <h2>Subjects and allocations</h2>
                </div>
                <div className="record-actions">
                  <button className="icon-button" title="Edit semester" onClick={() => setEditingSemester(currentSemester)}><Pencil size={17} /></button>
                  <button className="icon-button danger" title="Delete semester" onClick={confirmDeleteSemester}><Trash2 size={17} /></button>
                  <button className="primary" disabled={!optionsQ.data?.faculty.length || !optionsQ.data?.rooms.length} onClick={() => setAddingSubject(true)}>Add subject</button>
                </div>
              </div>
              {coursesQ.data?.items.length ? (
                <div className="offering-grid">
                  {coursesQ.data.items.map((o: any) => (
                    <div className={`offering ${o.kind}`} key={o.id}>
                      <div className="offering-head">
                        <div><span className="badge">{o.kind}</span><h3>{o.code} · {o.name}</h3></div>
                        <div className="record-actions">
                          <button className="icon-button" title="Edit subject" onClick={() => setEditingSubject(o)}><Pencil size={15} /></button>
                          <button className="icon-button danger" title="Delete subject" onClick={() => confirmDeleteSubject(o)}><Trash2 size={15} /></button>
                        </div>
                      </div>
                      <div className="offering-meta">
                        <span>
                          <Clock3 /> {o.kind === "lab" ? `${o.sessions_per_week} lab session${o.sessions_per_week > 1 ? "s" : ""}` : `${o.theory_sessions_per_week || 0} theory + ${o.lecture_sessions_per_week || 0} lecture/tutorial`}
                        </span>
                        <span>
                          <Users /> {o.enrollment} students
                        </span>
                        <span>
                          <Users /> {facultyNames(optionsQ.data, o.faculty_ids)}
                        </span>
                        <span>
                          <Building2 />{" "}
                          {roomNames(optionsQ.data, o.eligible_room_ids)}
                        </span>
                      </div>
                      {o.elective_group && (
                        <small>
                          Parallel elective group: {o.elective_group}
                        </small>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState text="No subjects added for this semester." />
              )}
            </div>
          </>
        )}
      </div>
      {validation.data && (
        <div className={validation.data.valid ? "validation-ok" : "error"}>
          {validation.data.valid ? (
            <>
              <ShieldCheck />
              Configuration is complete and solver-ready.
            </>
          ) : (
            validation.data.errors.map((e) => (
              <div key={e.code}>{e.message}</div>
            ))
          )}
        </div>
      )}
      {(addingSemester || editingSemester) && yearId && optionsQ.data && (
        <SemesterForm
          yearId={yearId}
          termType={statusQ.data?.active_year?.term_type || "odd"}
          options={optionsQ.data}
          initial={editingSemester}
          close={() => { setAddingSemester(false); setEditingSemester(null); }}
        />
      )}{" "}
      {(addingSubject || editingSubject) && current && optionsQ.data && (
        <SubjectForm
          semesterId={current}
          options={optionsQ.data}
          initial={editingSubject}
          close={() => { setAddingSubject(false); setEditingSubject(null); }}
        />
      )}
      {(deleteSemester.error || deleteSubject.error || createCohorts.error) && <div className="error">{errorText(deleteSemester.error || deleteSubject.error || createCohorts.error)}</div>}
      {foundationEdit && <FoundationForm {...foundationEdit} close={() => setFoundationEdit(null)} done={refresh} />}
      {editingWeek && <WorkingWeekForm initial={optionsQ.data?.time_slots} close={() => setEditingWeek(false)} done={refresh} />}
      {(deleteFoundation.error || deleteWeek.error) && <div className="error">{errorText(deleteFoundation.error || deleteWeek.error)}</div>}
    </section>
  );
}
function SetupChecklist({ status }: { status?: SetupStatus }) {
  return (
    <div className="flow-strip">
      {status?.steps.map((s, i) => (
        <div className={s.complete ? "complete" : ""} key={s.key}>
          <span>{s.complete ? <Check size={15} /> : i + 1}</span>
          <strong>{s.label}</strong>
        </div>
      ))}
    </div>
  );
}
function CompleteCard({ title, onEdit, onDelete }: { title: string; onEdit?: () => void; onDelete?: () => void }) {
  return (
    <div className="quick-card complete-card">
      <ShieldCheck />
      <h3>{title}</h3>
      <p>Configured</p>
      {(onEdit || onDelete) && <div className="record-actions"><button className="icon-button" title="Edit" onClick={onEdit}><Pencil size={15}/></button>{onDelete && <button className="icon-button danger" title="Delete" onClick={onDelete}><Trash2 size={15}/></button>}</div>}
    </div>
  );
}
function FoundationForm({resource,item,fields,close,done}:{resource:string;item:any;fields:string[][];close:()=>void;done:()=>void}){
  const [form,setForm]=useState<any>(Object.fromEntries(fields.map(([key])=>[key,item[key]])));
  const mutation=useMutation({mutationFn:()=>setupUpdate(resource,item.id,form),onSuccess:()=>{done();close()}});
  return <Modal title={`Edit ${resource.replace("academic-years","academic year").replace("institutes","institute").replace("departments","department")}`} close={close} submit={()=>mutation.mutate()} pending={mutation.isPending} error={mutation.error}>{fields.map(([key,label,type])=><label key={key}>{label}{type === "term" ? <select value={form[key] || "odd"} onChange={e=>setForm({...form,[key]:e.target.value})}><option value="odd">Odd · Semesters 3, 5, 7</option><option value="even">Even · Semesters 2, 4, 6</option></select> : <input required value={form[key]||""} onChange={e=>setForm({...form,[key]:e.target.value})}/>}</label>)}</Modal>
}
function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty">
      <BookOpen />
      <p>{text}</p>
    </div>
  );
}
function QuickForm({
  title,
  fields,
  submit,
  done,
}: {
  title: string;
  fields: string[][];
  submit: (d: any) => Promise<any>;
  done: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(() => Object.fromEntries(fields.filter(([, , type]) => type === "term").map(([key]) => [key, "odd"])));
  const mutation = useMutation({
    mutationFn: () => submit(form),
    onSuccess: () => {
      setForm({});
      done();
    },
  });
  return (
    <form
      className="quick-card"
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
    >
      <h3>{title}</h3>
      {fields.map(([key, label, type]) => (
        <label key={key}>
          {label}
          {type === "term" ? <select value={form[key] || "odd"} onChange={(e) => setForm({ ...form, [key]: e.target.value })}><option value="odd">Odd · Semesters 3, 5, 7</option><option value="even">Even · Semesters 2, 4, 6</option></select> : <input
            required
            value={form[key] || ""}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          />}
        </label>
      ))}
      {mutation.error && (
        <div className="error">{errorText(mutation.error)}</div>
      )}
      <button className="secondary" disabled={mutation.isPending}>
        Save {title.toLowerCase()}
      </button>
    </form>
  );
}
function WorkingWeekForm({ done, initial, close }: { done: () => void; initial?: any[]; close?: () => void }) {
  const firstDay=initial?.[0]?.day;const daySlots=(initial||[]).filter(slot=>slot.day===firstDay);const lunch=daySlots.find(slot=>slot.blocked);
  const [form, setForm] = useState({days: initial?.length ? DAYS.filter(day=>initial.some(slot=>slot.day===day)) : DAYS,start_hour: daySlots.length?Number(daySlots[0].start_time.split(":")[0]):9,periods_per_day: daySlots.length||8,lunch_after_period: lunch?.period_index??3});
  const mutation = useMutation({
    mutationFn: () => initial?.length ? setupUpdateRoot("working-week", form) : setupCreate("working-week", form),
    onSuccess: () => {done();close?.()},
  });
  const fields=<>
      <label>
        Days
        <input
          value={form.days.join(", ")}
          onChange={(e) =>
            setForm({
              ...form,
              days: e.target.value
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean),
            })
          }
        />
      </label>
      <label>
        First class hour
        <input
          type="number"
          min="0"
          max="11"
          value={form.start_hour}
          onChange={(e) =>
            setForm({ ...form, start_hour: Number(e.target.value) })
          }
        />
      </label>
      <label>
        Periods per day
        <input
          type="number"
          value={form.periods_per_day}
          onChange={(e) => {
            const periods = Number(e.target.value);
            setForm({ ...form, periods_per_day: periods, lunch_after_period: Math.min(form.lunch_after_period, Math.max(0, periods - 1)) });
          }}
        />
      </label>
      <label>
        Lunch break
        <select value={form.lunch_after_period} onChange={(e) => setForm({ ...form, lunch_after_period: Number(e.target.value) })}>
          {Array.from({ length: form.periods_per_day }, (_, index) => {
            const start = form.start_hour + index;
            return <option value={index} key={index}>{String(start).padStart(2, "0")}:00–{String(start + 1).padStart(2, "0")}:00</option>;
          })}
        </select>
      </label>
      <small>Select the institution's lunch timing. This period is blocked for every semester, room, and teacher.</small>
      {mutation.error && (
        <div className="error">{errorText(mutation.error)}</div>
      )}
    </>;
  if(initial?.length)return <Modal title="Edit working week" close={close!} submit={()=>mutation.mutate()} pending={mutation.isPending} error={mutation.error}>{fields}</Modal>;
  return <form className="quick-card" onSubmit={(e)=>{e.preventDefault();mutation.mutate()}}><h3>Working week</h3>{fields}<button className="secondary">Save working hours</button></form>;
}
function SemesterForm({
  yearId,
  termType,
  options,
  initial,
  close,
}: {
  yearId: number;
  termType: "odd" | "even";
  options: any;
  initial?: any;
  close: () => void;
}) {
  const qc = useQueryClient();
  const rooms = options.rooms.filter((r: any) => r.room_type === "theory");
  const [form, setForm] = useState(initial ? {
    academic_year_id: initial.academic_year_id,
    department_id: initial.department_id,
    semester_number: initial.semester_number,
    strength: initial.strength,
    home_room_id: initial.home_room_id,
    home_room_policy: initial.home_room_policy,
  } : { academic_year_id: yearId, department_id: options.departments[0]?.id, semester_number: termType === "odd" ? 3 : 2, strength: 60, home_room_id: null, home_room_policy: "disabled" });
  const mutation = useMutation({
    mutationFn: () => initial ? setupUpdate("semesters", initial.id, form) : setupCreate("semesters", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["semesters"] });
      qc.invalidateQueries({ queryKey: ["setup-status"] });
      close();
    },
  });
  return (
    <Modal
      title={initial ? "Edit semester cohort" : "Add semester cohort"}
      close={close}
      submit={() => mutation.mutate()}
      pending={mutation.isPending}
      error={mutation.error}
    >
      <label>
        Department
        <select
          value={form.department_id}
          onChange={(e) =>
            setForm({ ...form, department_id: Number(e.target.value) })
          }
        >
          {options.departments.map((d: any) => (
            <option key={d.id} value={d.id}>
              {d.code} · {d.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Semester
        <select
          value={form.semester_number}
          onChange={(e) =>
            setForm({ ...form, semester_number: Number(e.target.value) })
          }
        >
          {(termType === "odd" ? [3, 5, 7] : [2, 4, 6]).map((n) => (
            <option key={n} value={n}>
              Semester {roman(n)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Class strength
        <input
          type="number"
          min="1"
          value={form.strength}
          onChange={(e) =>
            setForm({ ...form, strength: Number(e.target.value) })
          }
        />
      </label>
      <label>
        Home classroom
        <select
          value={form.home_room_id || ""}
          onChange={(e) =>
            setForm({ ...form, home_room_id: e.target.value ? Number(e.target.value) : null, home_room_policy: e.target.value ? "hard" : "disabled" })
          }
        >
          <option value="">Automatic compatible classroom</option>
          {rooms.map((r: any) => (
            <option key={r.id} value={r.id}>
              {r.code} · capacity {r.capacity}
            </option>
          ))}
        </select>
      </label>
    </Modal>
  );
}
function Modal({
  title,
  close,
  submit,
  pending,
  submitDisabled = false,
  wide = false,
  error,
  children,
}: {
  title: string;
  close: () => void;
  submit: () => void;
  pending: boolean;
  submitDisabled?: boolean;
  wide?: boolean;
  error: unknown;
  children: React.ReactNode;
}) {
  return (
    <div className="modal-backdrop">
      <form
        className={`modal ${wide ? "wide-modal" : ""}`}
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          submit();
        }}
      >
        <div className="modal-head">
          <div>
            <p className="eyebrow">Admin entry</p>
            <h2>{title}</h2>
          </div>
          <button type="button" className="icon-button" onClick={close}>
            <X />
          </button>
        </div>
        <div className="form-grid">{children}</div>
        {!!error && <div className="error">{errorText(error)}</div>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={pending || submitDisabled}>
            {pending ? "Saving…" : "Save record"}
          </button>
        </div>
      </form>
    </div>
  );
}

function roman(n: number) {
  return (
    ({ 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII" } as Record<number, string>)[n] || String(n)
  );
}
function facultyNames(options: any, ids: number[]) {
  return ids
    .map(
      (id) =>
        options?.faculty.find((f: any) => f.id === id)?.name ||
        `Faculty #${id}`,
    )
    .join(", ");
}
function roomNames(options: any, ids: number[]) {
  if (!ids?.length) return "Automatic compatible room";
  return ids.map((id) => roomName(options, id)).join(", ");
}
function roomName(options: any, id: number) {
  if (!id) return "Automatic room allocation";
  const r = options?.rooms.find((x: any) => x.id === id);
  return r ? `${r.code} · ${r.name}` : `Room #${id}`;
}
function SubjectForm({
  semesterId,
  options,
  initial,
  close,
}: {
  semesterId: number;
  options: any;
  initial?: any;
  close: () => void;
}) {
  const qc = useQueryClient();
  const firstFacultyId = options.faculty[0]?.id;
  const [form, setForm] = useState<any>(initial ? {
    ...initial,
    theory_sessions_per_week: initial.kind === "lab" ? 0 : (initial.theory_sessions_per_week || initial.sessions_per_week || 0),
    lecture_sessions_per_week: initial.lecture_sessions_per_week || 0,
    theory_faculty_ids: initial.theory_faculty_ids?.length ? initial.theory_faculty_ids : initial.faculty_ids,
    lecture_faculty_ids: initial.lecture_faculty_ids || [],
    participant_group: initial.participant_group_ids?.[0] || null,
  } : {
    semester_offering_id: semesterId,
    code: "",
    name: "",
    kind: "theory",
    sessions_per_week: 3,
    theory_sessions_per_week: 2,
    lecture_sessions_per_week: 1,
    duration_periods: 1,
    enrollment: 60,
    faculty_ids: firstFacultyId ? [firstFacultyId] : [],
    theory_faculty_ids: firstFacultyId ? [firstFacultyId] : [],
    lecture_faculty_ids: firstFacultyId ? [firstFacultyId] : [],
    eligible_room_ids: [],
    required_features: [],
    participant_group: null,
    elective_group: null,
    parallel_elective: false,
    fixed_day: null,
    fixed_period: null,
    fixed_room_id: null,
  });
  const [requiredCapabilitiesText, setRequiredCapabilitiesText] = useState(
    (initial?.required_features || []).join("\n"),
  );
  const [labCategory, setLabCategory] = useState<"regular" | "elective">("regular");
  const createBatchRows = (count: number, existing: any[] = []) =>
    Array.from({ length: count }, (_, index) => existing[index] || ({
      participant_group: `B${index + 1}`,
      faculty_ids: firstFacultyId ? [firstFacultyId] : [],
      room_id: null,
    }));
  const [batchAllocations, setBatchAllocations] = useState<any[]>(() => createBatchRows(4));
  const updateBatch = (index: number, changes: Record<string, any>) => {
    setBatchAllocations((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, ...changes } : row));
  };
  const selectLabCategory = (category: "regular" | "elective") => {
    setLabCategory(category);
    setBatchAllocations((rows) => createBatchRows(category === "elective" ? 2 : 4, rows));
  };
  const copyFirstBatch = () => {
    setBatchAllocations((rows) => rows.map((row, index) => index === 0 ? row : ({
      ...row,
      faculty_ids: [...rows[0].faculty_ids],
      room_id: rows[0].room_id,
    })));
  };
  const batchInvalid = !initial && form.kind === "lab" && batchAllocations.some(
    (batch) => !batch.participant_group.trim() || !batch.faculty_ids.length,
  );
  const componentInvalid = form.kind !== "lab" && (
    form.theory_sessions_per_week + form.lecture_sessions_per_week < 1 ||
    (!!form.theory_sessions_per_week && !form.theory_faculty_ids.length) ||
    (!!form.lecture_sessions_per_week && !form.lecture_faculty_ids.length)
  );
  const mutation = useMutation({
    mutationFn: () => {
      const payload = {
        ...form,
        sessions_per_week: form.kind === "lab" ? form.sessions_per_week : form.theory_sessions_per_week + form.lecture_sessions_per_week,
        faculty_ids: form.kind === "lab" ? form.faculty_ids : Array.from(new Set([...(form.theory_faculty_ids || []), ...(form.lecture_faculty_ids || [])])),
        required_features: splitCapabilities(requiredCapabilitiesText),
      };
      if (!initial && form.kind === "lab") {
        return addLabBatchOfferings({
          semester_offering_id: semesterId,
          code: form.code,
          name: form.name,
          sessions_per_week: form.sessions_per_week,
          total_enrollment: form.enrollment,
          required_features: payload.required_features,
          elective_lab: labCategory === "elective",
          batches: batchAllocations,
        });
      }
      return initial ? updateOffering(initial.id, payload) : addOffering(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["offerings", semesterId] });
      qc.invalidateQueries({ queryKey: ["setup-status"] });
      close();
    },
  });
  const set = (key: string, value: any) => setForm({ ...form, [key]: value });
  const selectKind = (kind: string) => {
    setForm({
      ...form,
      kind,
      duration_periods: kind === "lab" ? 2 : 1,
      theory_sessions_per_week: kind === "lab" ? 0 : (form.theory_sessions_per_week || 2),
      lecture_sessions_per_week: kind === "lab" ? 0 : (form.lecture_sessions_per_week || 1),
      eligible_room_ids: [],
    });
  };
  return (
    <Modal
      title={initial ? "Edit subject and allocation" : form.kind === "lab" ? "Add lab and allocate every batch" : "Add subject and allocation"}
      close={close}
      submit={() => mutation.mutate()}
      pending={mutation.isPending}
      submitDisabled={batchInvalid || componentInvalid}
      wide={!initial && form.kind === "lab"}
      error={mutation.error}
    >
      <label>
        Subject code
        <input
          required
          value={form.code}
          onChange={(e) => set("code", e.target.value)}
        />
      </label>
      <label>
        Subject name
        <input
          required
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
        />
      </label>
      <label>
        Activity type
        <select value={form.kind} onChange={(e) => selectKind(e.target.value)}>
          <option value="theory">Theory</option>
          <option value="lab">Laboratory</option>
          <option value="elective">Elective</option>
        </select>
      </label>
      {!initial && form.kind === "lab" && (
        <fieldset className="multi-select-field lab-category-field">
          <legend>Lab batch pattern</legend>
          <div className="lab-category-options">
            <label className={labCategory === "regular" ? "selected" : ""}>
              <input type="radio" name="lab-category" checked={labCategory === "regular"} onChange={() => selectLabCategory("regular")} />
              <span><strong>Regular lab</strong><small>4 batches · B1 to B4</small></span>
            </label>
            <label className={labCategory === "elective" ? "selected" : ""}>
              <input type="radio" name="lab-category" checked={labCategory === "elective"} onChange={() => selectLabCategory("elective")} />
              <span><strong>Elective lab</strong><small>2 batches · B1 and B2</small></span>
            </label>
          </div>
        </fieldset>
      )}
      {form.kind === "lab" ? <label>
        Lab sessions per week
        <input type="number" min="1" max="10" value={form.sessions_per_week} onChange={(e) => set("sessions_per_week", Number(e.target.value))} />
      </label> : <div className="component-counts">
        <label>Theory classes per week<input type="number" min="0" max="10" value={form.theory_sessions_per_week} onChange={(e) => set("theory_sessions_per_week", Number(e.target.value))} /></label>
        <label>Lecture/tutorial classes per week<input type="number" min="0" max="10" value={form.lecture_sessions_per_week} onChange={(e) => set("lecture_sessions_per_week", Number(e.target.value))} /></label>
        <small className="muted">Example: 2 theory + 1 lecture/tutorial. Each component may use the same or different teachers.</small>
      </div>}
      <label>
        Duration in periods
        <input
          type="number"
          min={form.kind === "lab" ? 2 : 1}
          max={form.kind === "lab" ? 2 : 4}
          disabled={form.kind === "lab"}
          value={form.duration_periods}
          onChange={(e) => set("duration_periods", Number(e.target.value))}
        />
      </label>
      <label>
        {!initial && form.kind === "lab" ? "Total semester students" : "Students enrolled"}
        <input
          type="number"
          min="1"
          value={form.enrollment}
          onChange={(e) => set("enrollment", Number(e.target.value))}
        />
      </label>
      {form.kind !== "lab" && <>
        <fieldset className="multi-select-field">
          <legend>Theory faculty · select one or more</legend>
          <div className="check-list">
            {options.faculty.map((f: any) => {
              const checked = form.theory_faculty_ids.includes(f.id);
              return <label className="checkbox" key={f.id}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!form.theory_sessions_per_week}
                  onChange={() => set("theory_faculty_ids", checked ? form.theory_faculty_ids.filter((id: number) => id !== f.id) : [...form.theory_faculty_ids, f.id])}
                />
                {f.faculty_code} · {f.name}
              </label>;
            })}
          </div>
          {!!form.theory_sessions_per_week && !form.theory_faculty_ids.length && <small className="field-error">Select at least one theory teacher.</small>}
        </fieldset>
        <fieldset className="multi-select-field">
          <legend>Lecture/tutorial faculty · select one or more</legend>
          <div className="check-list">
            {options.faculty.map((f: any) => {
              const checked = form.lecture_faculty_ids.includes(f.id);
              return <label className="checkbox" key={f.id}>
                <input type="checkbox" checked={checked} disabled={!form.lecture_sessions_per_week} onChange={() => set("lecture_faculty_ids", checked ? form.lecture_faculty_ids.filter((id: number) => id !== f.id) : [...form.lecture_faculty_ids, f.id])} />
                {f.faculty_code} · {f.name}
              </label>;
            })}
          </div>
          {!!form.lecture_sessions_per_week && !form.lecture_faculty_ids.length && <small className="field-error">Select at least one lecture/tutorial teacher.</small>}
        </fieldset>
        <fieldset className="multi-select-field">
          <legend>{form.kind === "lab" ? "Allowed laboratories" : "Allowed classrooms"} · optional</legend>
          <p className="muted">Leave every option unchecked to let the optimizer select any compatible room automatically.</p>
          <div className="check-list">
            {options.rooms.filter((room: any) => form.kind === "lab" ? room.room_type === "lab" : room.room_type === "theory").map((room: any) => {
              const checked = form.eligible_room_ids.includes(room.id);
              return <label className="checkbox" key={room.id}><input type="checkbox" checked={checked} onChange={() => set("eligible_room_ids", checked ? form.eligible_room_ids.filter((id: number) => id !== room.id) : [...form.eligible_room_ids, room.id])} />{room.code} · {room.name} · capacity {room.capacity}{room.concurrent_capacity > 1 ? ` · ${room.concurrent_capacity} simultaneous groups` : ""}</label>;
            })}
          </div>
        </fieldset>
      </>}
      {form.kind === "lab" && initial && <fieldset className="multi-select-field">
        <legend>Lab faculty · select one or more</legend>
        <div className="check-list">{options.faculty.map((f: any) => { const checked = form.faculty_ids.includes(f.id); return <label className="checkbox" key={f.id}><input type="checkbox" checked={checked} onChange={() => set("faculty_ids", checked ? form.faculty_ids.filter((id: number) => id !== f.id) : [...form.faculty_ids, f.id])} />{f.faculty_code} · {f.name}</label>; })}</div>
      </fieldset>}
      {form.kind === "lab" && (
        <>
          {initial && <label>
            Batch/group name
            <input required placeholder="Example: SEM-5-B1" value={form.participant_group || ""} onChange={(e) => set("participant_group", e.target.value)} />
          </label>}
          <label>
            Required lab capabilities
            <textarea placeholder={"One per line, or separated by commas/semicolons\nExample: Network Lab; Electrical Machines"} value={requiredCapabilitiesText} onChange={(e) => setRequiredCapabilitiesText(e.target.value)} />
            <small>The optimizer will only use labs whose supported subjects/capabilities include these values.</small>
          </label>
          {!initial && (
            <fieldset className="multi-select-field batch-allocation-field">
              <div className="batch-allocation-head">
                <div><legend>Batch-wise faculty and laboratory allocation</legend><p className="muted">Choose a room for each batch, or leave Automatic so the generator selects a compatible lab.</p></div>
                <button type="button" className="secondary" onClick={copyFirstBatch}>Copy B1 allocation to all</button>
              </div>
              <div className="batch-allocation-grid">
                {batchAllocations.map((batch, index) => (
                  <section className="batch-allocation-card" key={index}>
                    <h3>Batch {index + 1}</h3>
                    <label>
                      Batch name
                      <input required value={batch.participant_group} onChange={(event) => updateBatch(index, { participant_group: event.target.value })} />
                    </label>
                    <label>
                      Laboratory
                      <select value={batch.room_id || ""} onChange={(event) => updateBatch(index, { room_id: event.target.value ? Number(event.target.value) : null })}>
                        <option value="">Automatic compatible lab</option>
                        {options.rooms.filter((room: any) => room.room_type === "lab").map((room: any) => (
                          <option key={room.id} value={room.id}>{room.code} · {room.name} · capacity {room.capacity}</option>
                        ))}
                      </select>
                    </label>
                    <div className="batch-faculty">
                      <strong>Faculty · one or more</strong>
                      <div className="check-list compact-check-list">
                        {options.faculty.map((faculty: any) => {
                          const checked = batch.faculty_ids.includes(faculty.id);
                          return <label className="checkbox" key={faculty.id}>
                            <input type="checkbox" checked={checked} onChange={() => updateBatch(index, { faculty_ids: checked ? batch.faculty_ids.filter((id: number) => id !== faculty.id) : [...batch.faculty_ids, faculty.id] })} />
                            {faculty.faculty_code} · {faculty.name}
                          </label>;
                        })}
                      </div>
                      {!batch.faculty_ids.length && <small className="field-error">Select at least one teacher.</small>}
                    </div>
                  </section>
                ))}
              </div>
            </fieldset>
          )}
        </>
      )}
      {form.kind === "elective" && (
        <>
          <label>
            Elective group
            <input
              required
              placeholder="Example: SEM-7-ELECTIVE"
              value={form.elective_group || ""}
              onChange={(e) => set("elective_group", e.target.value)}
            />
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.parallel_elective}
              onChange={(e) => set("parallel_elective", e.target.checked)}
            />{" "}
            Schedule alternatives together
          </label>
        </>
      )}
    </Modal>
  );
}

function Generate() {
  const qc = useQueryClient();
  const existingTimetable = useQuery({ queryKey: ["timetable"], queryFn: () => timetable(), retry: false });
  const statusQ = useQuery({
    queryKey: ["setup-status"],
    queryFn: setupStatus,
  });
  const yearId = statusQ.data?.active_year?.id;
  const semQ = useQuery({
    queryKey: ["semesters", yearId],
    queryFn: () => semesters(yearId!),
    enabled: !!yearId,
  });
  const ids = (semQ.data?.items || []).map((x) => x.id);
  const check = useMutation({ mutationFn: () => validateSetup(yearId!, ids) });
  const mutation = useMutation({
    mutationFn: (mode: string) =>
      request<any>("/generation", {
        method: "POST",
        body: JSON.stringify({
          academic_year_id: yearId,
          semester_offering_ids: ids,
          solver_mode: mode,
          time_limit_seconds: 20,
          random_seed: 42,
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timetable"] }),
  });
  const [mode, setMode] = useState("hybrid");
  const begin = async () => {
    const result = await check.mutateAsync();
    if (result.valid) mutation.mutate(mode);
  };
  const ready = !!statusQ.data?.ready_for_validation && ids.length === 3;
  return (
    <section className="page">
      <PageTitle eyebrow="Optimization engine" title="Validate and generate" />
      <div className="grid-2">
        <div className="card">
          <h3>Pre-generation gate</h3>
          {!ready && (
            <div className="warning">
              Setup is incomplete. Return to Start Setup and finish every
              required category.
            </div>
          )}
          <div className="summary-list">
            <span>
              Academic year
              <strong>
                {statusQ.data?.active_year?.name || "Not configured"}
              </strong>
            </span>
            <span>
              Academic term<strong>{statusQ.data?.active_year?.term_type?.toUpperCase() || "Not configured"} · {statusQ.data?.active_year?.term_type === "even" ? "Semesters 2, 4, 6" : "Semesters 3, 5, 7"}</strong>
            </span>
            <span>
              Source<strong>Admin-entered records only</strong>
            </span>
            <span>
              Cross-checking<strong>Before and after solving</strong>
            </span>
          </div>
          <label>
            Optimization mode
            <select value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="cp_sat">CP-SAT only</option>
              <option value="hybrid">CP-SAT + gap minimization</option>
            </select>
          </label>
          <button
            className="primary wide"
            disabled={!ready || mutation.isPending || check.isPending}
            onClick={begin}
          >
            {mutation.isPending
              ? "Optimizing resources…"
              : check.isPending
                ? "Cross-checking inputs…"
                : existingTimetable.data ? "Cross-check & regenerate all" : "Cross-check & generate"}
            <Play size={17} />
          </button>
          {check.data && !check.data.valid && (
            <div className="error">
              {check.data.errors.map((e) => (
                <div key={e.code}>{e.message}</div>
              ))}
            </div>
          )}
          {mutation.error && (
            <div className="error">{errorText(mutation.error)}</div>
          )}
          {existingTimetable.data && <p className="muted">This creates a completely regenerated version {existingTimetable.data.version + 1}. For a targeted faculty or room disruption with minimum changes, use the Reschedule page.</p>}
        </div>
        <div className="card result">
          <h3>Generation result</h3>
          {!mutation.data ? (
            <div className="empty">
              <FlaskConical />
              <p>
                No timetable is generated until the complete setup passes
                validation.
              </p>
            </div>
          ) : (
            <>
              <div
                className={`result-status ${mutation.data.valid ? "success" : "failure"}`}
              >
                <ShieldCheck />
                <div>
                  <strong>{mutation.data.status.toUpperCase()}</strong>
                  <span>
                    {mutation.data.valid
                      ? "Independent validator passed"
                      : "Validation failed"}
                  </span>
                </div>
              </div>
              <div className="metric-grid compact">
                <Metric
                  label="Sessions"
                  value={String(mutation.data.metrics?.scheduled_sessions ?? 0)}
                  detail="All cohorts"
                  icon={<BookOpen />}
                />
                <Metric
                  label="Student gaps"
                  value={String(mutation.data.metrics?.student_gaps ?? 0)}
                  detail="Minimized"
                  icon={<Clock3 />}
                />
                <Metric
                  label="Room changes"
                  value={String(mutation.data.metrics?.student_room_changes ?? 0)}
                  detail="Between adjacent classes"
                  icon={<Building2 />}
                />
              </div>
              {!mutation.data.valid && !!mutation.data.diagnostics?.length && (
                <div className="error generation-diagnostics">
                  <strong>Why generation stopped</strong>
                  {mutation.data.diagnostics.map((diagnostic: any, index: number) => (
                    <div key={`${diagnostic.code || "diagnostic"}-${index}`}>
                      {diagnostic.message || String(diagnostic)}
                    </div>
                  ))}
                </div>
              )}
              <NavLink className="secondary button-link" to="/timetable">
                Review timetable
              </NavLink>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function ReschedulePage() {
  const qc = useQueryClient();
  const timetableQ = useQuery({ queryKey: ["timetable"], queryFn: () => timetable(), retry: false });
  const facultyQ = useQuery({ queryKey: ["faculty"], queryFn: () => list("faculty") });
  const roomsQ = useQuery({ queryKey: ["rooms"], queryFn: () => list("rooms") });
  const historyQ = useQuery({ queryKey: ["reschedule-history"], queryFn: rescheduleHistory });
  const [form, setForm] = useState({
    resource_type: "faculty" as "faculty" | "room",
    resource_id: 0,
    day: "Monday",
    start_period: 0,
    duration_periods: 1,
    reason: "",
  });
  const [previewedRequest, setPreviewedRequest] = useState<RescheduleRequest | null>(null);
  const preview = useMutation({
    mutationFn: previewReschedule,
    onSuccess: (_result, variables) => setPreviewedRequest(variables),
  });
  const apply = useMutation({
    mutationFn: applyReschedule,
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["timetable"] }),
        qc.invalidateQueries({ queryKey: ["reschedule-history"] }),
        qc.invalidateQueries({ queryKey: ["analytics"] }),
      ]);
      setPreviewedRequest(null);
    },
  });
  const data = timetableQ.data;
  const configuredDays = DAYS.filter((day) => data?.time_slots.some((slot: any) => slot.day === day));
  const daySlots = (data?.time_slots || [])
    .filter((slot: any) => slot.day === form.day)
    .sort((a: any, b: any) => a.period_index - b.period_index);
  const resources = form.resource_type === "faculty" ? facultyQ.data?.items || [] : roomsQ.data?.items || [];
  const requestBody = (): RescheduleRequest => ({
    source_timetable_id: data!.id,
    ...form,
    time_limit_seconds: 20,
    random_seed: 42,
  });
  const change = (values: Partial<typeof form>) => {
    setForm((current) => ({ ...current, ...values }));
    preview.reset();
    apply.reset();
    setPreviewedRequest(null);
  };
  const timeLabel = (day: string, start: number, duration: number) => {
    const slots = (data?.time_slots || []).filter((slot: any) => slot.day === day);
    const first = slots.find((slot: any) => slot.period_index === start);
    const last = slots.find((slot: any) => slot.period_index === start + duration - 1);
    return first && last ? `${first.start_time}–${last.end_time}` : `Period ${start + 1}`;
  };
  const plan = apply.data || preview.data;
  const canPreview = !!data && !!form.resource_id && form.reason.trim().length >= 3;
  return (
    <section className="page">
      <PageTitle eyebrow="Quality-preserving change engine" title="Dynamic rescheduling" />
      <p className="lead">Temporarily block a teacher or room, then find a small bounded set of valid changes without accepting avoidable student gaps. A new version is created only after approval.</p>
      <div className="reschedule-layout">
        <div className="card reschedule-form">
          <h3>Report a disruption</h3>
          {timetableQ.error && <div className="error">Generate a timetable before using dynamic rescheduling.</div>}
          <div className="version-banner">
            <span>Source timetable</span>
            <strong>{data ? `Version ${data.version} · ${data.academic_year}` : "Loading…"}</strong>
          </div>
          <div className="form-grid">
            <label>
              Unavailable resource
              <select value={form.resource_type} onChange={(event) => change({ resource_type: event.target.value as "faculty" | "room", resource_id: 0 })}>
                <option value="faculty">Faculty member</option>
                <option value="room">Room / laboratory</option>
              </select>
            </label>
            <label>
              {form.resource_type === "faculty" ? "Faculty" : "Room / laboratory"}
              <select required value={form.resource_id || ""} onChange={(event) => change({ resource_id: Number(event.target.value) })}>
                <option value="">Select {form.resource_type}</option>
                {resources.map((resource: any) => <option key={resource.id} value={resource.id}>
                  {form.resource_type === "faculty" ? `${resource.faculty_code} · ${resource.name}` : `${resource.code} · ${resource.name}`}
                </option>)}
              </select>
            </label>
            <label>
              Day
              <select value={form.day} onChange={(event) => change({ day: event.target.value, start_period: 0 })}>
                {configuredDays.map((day) => <option key={day}>{day}</option>)}
              </select>
            </label>
            <label>
              Starting time
              <select value={form.start_period} onChange={(event) => change({ start_period: Number(event.target.value) })}>
                {daySlots.filter((slot: any) => !slot.blocked).map((slot: any) => <option key={slot.period_index} value={slot.period_index}>{slot.start_time}–{slot.end_time}</option>)}
              </select>
            </label>
            <label>
              Unavailable for
              <select value={form.duration_periods} onChange={(event) => change({ duration_periods: Number(event.target.value) })}>
                <option value={1}>1 period</option>
                <option value={2}>2 periods</option>
                <option value={3}>3 periods</option>
              </select>
            </label>
          </div>
          <label>
            Reason
            <textarea rows={3} placeholder="Example: University examination duty" value={form.reason} onChange={(event) => change({ reason: event.target.value })} />
          </label>
          <button className="primary wide" disabled={!canPreview || preview.isPending} onClick={() => preview.mutate(requestBody())}>
            {preview.isPending ? "Optimizing a valid low-gap alternative…" : "Preview rescheduling"}
            <RefreshCw size={17} />
          </button>
          {preview.error && <div className="error">{errorText(preview.error)}</div>}
        </div>

        <div className="card reschedule-preview">
          <h3>Before / after preview</h3>
          {!plan ? <div className="empty"><CalendarClock /><p>Select a disruption to see exactly which classes must move.</p></div> : <>
            <div className={`result-status ${plan.valid ? "success" : "failure"}`}>
              <ShieldCheck />
              <div><strong>{plan.valid ? "VALID ALTERNATIVE" : "NO VALID ALTERNATIVE"}</strong><span>{plan.resource_name} · {plan.affected_sessions} affected · {plan.moved_sessions} moved</span></div>
            </div>
            {plan.valid && <div className="validation-metrics reschedule-quality">
              <span><b>{plan.metrics.student_gaps ?? 0}</b> student gaps</span>
              <span><b>{plan.metrics.cohort_gaps ?? 0}</b> cohort gaps</span>
              <span><b>{plan.metrics.faculty_gaps ?? 0}</b> faculty gaps</span>
              <span><b>{plan.metrics.student_room_changes ?? 0}</b> room changes</span>
            </div>}
            {!!plan.changes.length && <div className="change-list">
              {plan.changes.map((item) => <article key={item.session_id} className="change-row">
                <div><span className="semester-chip">Sem {roman(item.semester_number)}</span><strong>{item.course_code} · {item.course_name}</strong><small>{item.participant_group_ids.join(", ")}</small></div>
                <div className="change-place before"><small>Before</small><strong>{item.before.day} · {timeLabel(item.before.day, item.before.start_period, item.before.duration_periods)}</strong><span>{item.before.room_code}</span></div>
                <ChevronRight />
                <div className="change-place after"><small>After</small><strong>{item.after.day} · {timeLabel(item.after.day, item.after.start_period, item.after.duration_periods)}</strong><span>{item.after.room_code}</span></div>
              </article>)}
            </div>}
            {!plan.changes.length && <div className="note-panel">{plan.diagnostics[0]?.message || "No classes need to move."}</div>}
            {!!plan.diagnostics.length && plan.status !== "no_change_needed" && !plan.valid && <div className="error generation-diagnostics"><strong>Why it cannot be applied</strong>{plan.diagnostics.map((item, index) => <div key={`${item.code}-${index}`}>{item.message || JSON.stringify(item)}</div>)}</div>}
            {previewedRequest && preview.data?.valid && preview.data.status !== "no_change_needed" && !apply.data && <button className="primary wide" disabled={apply.isPending} onClick={() => apply.mutate(previewedRequest)}>{apply.isPending ? "Rechecking and creating version…" : `Apply as version ${preview.data.source_version + 1}`}<Check size={17} /></button>}
            {apply.error && <div className="error">{errorText(apply.error)}</div>}
            {apply.data && <div className="success-panel"><strong>Version {apply.data.result_version} created successfully.</strong><span>The previous timetable remains preserved in history.</span><NavLink className="secondary button-link" to="/timetable">Open new timetable</NavLink></div>}
          </>}
        </div>
      </div>

      <div className="card reschedule-history">
        <h3>Rescheduling history</h3>
        {!historyQ.data?.items.length ? <p className="muted">No dynamic changes have been applied yet.</p> : <div className="history-list">{historyQ.data.items.map((item: any) => <div key={item.id}>
          <span className="history-version">v{item.source_version} → v{item.result_version}</span>
          <div><strong>{item.resource_name}</strong><small>{item.day} · {timeLabel(item.day, item.start_period, item.duration_periods)} · {item.reason}</small></div>
          <span>{item.moved_sessions} moved</span>
        </div>)}</div>}
      </div>
    </section>
  );
}

function TimetablePage({ user }: { user: User }) {
  const qc = useQueryClient();
  const [selectedVersion, setSelectedVersion] = useState<number | 0>(0);
  const [viewMode, setViewMode] = useState<"semester" | "faculty">(user.role === "faculty" ? "faculty" : "semester");
  const [selectedFaculty, setSelectedFaculty] = useState<number | 0>(user.faculty_id || 0);
  const historyQ = useQuery({ queryKey: ["timetable-history"], queryFn: () => timetableHistory() });
  const optionsQ = useQuery({ queryKey: ["setup-options"], queryFn: setupOptions, enabled: user.role === "admin" });
  const backupsQ = useQuery({ queryKey: ["timetable-backups"], queryFn: timetableBackups, enabled: user.role === "admin" });
  const q = useQuery({
    queryKey: ["timetable", selectedVersion],
    queryFn: () => timetable(selectedVersion || undefined),
    retry: false,
  });
  const validationQ = useQuery({
    queryKey: ["timetable-validation", q.data?.id],
    queryFn: () => timetableValidation(q.data!.id),
    enabled: Boolean(q.data?.id),
    retry: false,
  });
  const statusMutation = useMutation({
    mutationFn: (status: "draft" | "published" | "archived") => setTimetableStatus(q.data!.id, status),
    onSuccess: async () => {
      await Promise.all([qc.invalidateQueries({ queryKey: ["timetable"] }), qc.invalidateQueries({ queryKey: ["timetable-history"] })]);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteTimetable(q.data!.id),
    onSuccess: async () => {
      setSelectedVersion(0);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["timetable"] }),
        qc.invalidateQueries({ queryKey: ["timetable-history"] }),
        qc.invalidateQueries({ queryKey: ["timetable-backups"] }),
        qc.invalidateQueries({ queryKey: ["timetable-validation"] }),
      ]);
    },
  });
  const confirmDeleteVersion = () => {
    if (!q.data) return;
    const publishedWarning = q.data.status === "published" ? " This is the published timetable: student and faculty views will have no current timetable until another version is published." : "";
    if (window.confirm(`Delete timetable version ${q.data.version}?${publishedWarning} Its sessions, validation report, internal backup, and related rescheduling log will also be removed. A full recovery backup will be created automatically.`)) {
      deleteMutation.mutate();
    }
  };
  const [semester, setSemester] = useState<number | 0>(0);
  const semesterNumbers = useMemo(
    () =>
      [
        ...new Set(
          (q.data?.sessions || [])
            .map((s) => s.semester_number)
            .filter(Boolean) as number[],
        ),
      ].sort(),
    [q.data],
  );
  const shownSemesters = semester ? [semester] : semesterNumbers;
  const activeFacultyId = user.role === "faculty" ? user.faculty_id || 0 : selectedFaculty;
  const facultyName = user.role === "faculty" ? user.name : optionsQ.data?.faculty.find((item: any) => item.id === activeFacultyId)?.name || "Select faculty";
  const facultyCode = user.role === "faculty" ? "" : optionsQ.data?.faculty.find((item: any) => item.id === activeFacultyId)?.faculty_code || "";
  const facultySessions = (q.data?.sessions || []).filter((session) => !activeFacultyId || session.faculty_ids.includes(activeFacultyId));
  const currentBackup = backupsQ.data?.items.find((item: any) => item.timetable_id === q.data?.id);
  return (
    <section className="page">
      <PageTitle
        eyebrow="Generated schedule"
        title={
          viewMode === "faculty"
            ? `${facultyName} · faculty timetable`
            : semester
            ? `Semester ${roman(semester)} timetable`
            : "Master timetable"
        }
      >
        <div className="actions">
          <select value={selectedVersion} onChange={(e) => { setSelectedVersion(Number(e.target.value)); setSemester(0); }}>
            <option value={0}>Latest active term</option>
            {historyQ.data?.items.map((item: any) => <option key={item.id} value={item.id}>{item.academic_year} · {item.academic_term.toUpperCase()} · v{item.version} · {item.status}</option>)}
          </select>
          {(user.role === "admin" || user.role === "faculty") && <select value={viewMode} onChange={(event) => setViewMode(event.target.value as "semester" | "faculty")}>
            {user.role === "admin" && <option value="semester">Semester timetables</option>}
            <option value="faculty">Faculty timetable</option>
          </select>}
          {user.role === "admin" && viewMode === "faculty" && <select value={selectedFaculty} onChange={(event) => setSelectedFaculty(Number(event.target.value))}>
            <option value={0}>Select faculty</option>
            {optionsQ.data?.faculty.map((faculty: any) => <option key={faculty.id} value={faculty.id}>{faculty.faculty_code} · {faculty.name}</option>)}
          </select>}
          {viewMode === "semester" && <select
            value={semester}
            onChange={(e) => setSemester(Number(e.target.value))}
          >
            <option value={0}>All semesters</option>
            {semesterNumbers.map((n) => (
              <option value={n} key={n}>
                Semester {roman(n)}
              </option>
            ))}
          </select>}
          <button className="secondary" onClick={downloadCsv}>
            <Download size={17} />
            CSV
          </button>
          <button className="secondary" onClick={() => window.print()}>
            <Printer size={17} />
            Print
          </button>
          {user.role === "admin" && currentBackup && <button className="secondary" onClick={() => downloadTimetableBackup(currentBackup.id, q.data!.academic_year, q.data!.version)}>
            <ShieldCheck size={17} />
            Backup JSON
          </button>}
          {user.role === "admin" && q.data && <select className="status-select" value={q.data.status} disabled={statusMutation.isPending} onChange={(event) => statusMutation.mutate(event.target.value as "draft" | "published" | "archived")}>
            <option value="draft">Draft</option>
            <option value="published">Published / achieved backup</option>
            <option value="archived">Archived</option>
          </select>}
          {user.role === "admin" && q.data && <button className="secondary danger" disabled={deleteMutation.isPending} onClick={confirmDeleteVersion}><Trash2 size={17} />{deleteMutation.isPending ? "Deleting…" : `Delete v${q.data.version}`}</button>}
        </div>
      </PageTitle>
      {deleteMutation.error && <div className="error">{errorText(deleteMutation.error)}</div>}
      {q.isLoading ? (
        <div className="loading">Loading timetable…</div>
      ) : q.error ? (
        <EmptyState text="No generated timetable exists yet." />
      ) : (
        <><div className="timetable-record-banner"><span>{q.data!.academic_year} · {q.data!.academic_term.toUpperCase()} term</span><strong>Version {q.data!.version} · {q.data!.status.toUpperCase()}</strong><small>{q.data!.created_at ? formatIndiaDateTime(q.data!.created_at!) : "Stored timetable record"}{user.role === "admin" ? currentBackup ? ` · Backup verified ${currentBackup.checksum.slice(0, 12)}…` : " · Legacy version (download backup unavailable)" : ""}</small></div>
        {validationQ.data && <div className={`card validation-report screen-only ${validationQ.data.valid ? "passed" : "failed"}`}>
          <div className="validation-report-head"><div>{validationQ.data.valid ? <ShieldCheck /> : <X />}<span><strong>{validationQ.data.valid ? "All hard constraints passed" : "Validation issues detected"}</strong><small>Independent report for version {validationQ.data.version} · {validationQ.data.scheduled_sessions} scheduled sessions</small></span></div><span className="badge">{validationQ.data.status}</span></div>
          <div className="validation-metrics">
            <span><b>{validationQ.data.metrics.student_gaps ?? 0}</b> student gaps</span>
            <span><b>{validationQ.data.metrics.faculty_gaps ?? 0}</b> faculty gaps</span>
            <span><b>{validationQ.data.metrics.student_room_changes ?? 0}</b> room changes</span>
            <span><b>{Math.round((validationQ.data.metrics.room_utilization ?? 0) * 100)}%</b> room utilization</span>
          </div>
          {validationQ.data.errors?.length > 0 && <div className="generation-diagnostics">{validationQ.data.errors.map((item: any, index: number) => <small key={`${item.code}-${index}`}>{item.message || item.code}</small>)}</div>}
        </div>}
        <div className={`official-timetables ${viewMode}`}>
          {viewMode === "faculty" ? (
            activeFacultyId ? <div className="print-page"><FacultyTimetable data={q.data!} sessions={facultySessions} facultyName={facultyName} facultyCode={facultyCode} /></div> : <EmptyState text="Select a faculty member to view and print their timetable." />
          ) : shownSemesters.map((number) => (
            <div className="print-page" key={number}><InstitutionalTimetable data={q.data!} semester={number} /></div>
          ))}
        </div></>
      )}
    </section>
  );
}
async function downloadTimetableBackup(backupId: number, academicYear: string, version: number) {
  const data = await timetableBackup(backupId);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${academicYear.replaceAll(" ", "-")}-timetable-v${version}-backup.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function AccountPage({ user }: { user: User }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState("");
  const mutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword(""); setLocalError("");
    },
  });
  const submit = (event: FormEvent) => {
    event.preventDefault(); mutation.reset();
    if (newPassword !== confirmPassword) { setLocalError("New passwords do not match"); return; }
    setLocalError(""); mutation.mutate();
  };
  return <section className="page">
    <PageTitle eyebrow="Secure account" title="My account" />
    <div className="grid-2 account-layout">
      <div className="card account-summary"><ShieldCheck /><div><small>Signed in as</small><h2>{user.name}</h2><p>{user.email}</p><span className="badge">{user.role}</span></div></div>
      <form className="card password-form" onSubmit={submit}>
        <h3>Change password</h3>
        <p className="muted">Use at least 8 characters. This changes only your login and never modifies timetable data.</p>
        <label>Current password<input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
        <label>New password<input required minLength={8} type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <label>Confirm new password<input required minLength={8} type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
        {(localError || mutation.error) && <div className="error">{localError || errorText(mutation.error)}</div>}
        {mutation.isSuccess && <div className="validation-ok"><ShieldCheck />Password changed successfully.</div>}
        <button className="primary" disabled={mutation.isPending}>{mutation.isPending ? "Changing…" : "Change password"}</button>
      </form>
    </div>
  </section>;
}

async function downloadCsv() {
  const response = await fetch("/api/export/latest.csv", {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("timetable_token")}`,
    },
  });
  if (!response.ok) return;
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "timetable.csv";
  a.click();
  URL.revokeObjectURL(url);
}
function FacultyTimetable({ data, sessions, facultyName, facultyCode }: { data: any; sessions: Session[]; facultyName: string; facultyCode: string }) {
  const configuredDays = new Set(data.time_slots.map((slot: any) => slot.day));
  const days = DAYS.filter((day) => configuredDays.has(day));
  const periods = data.time_slots.filter((slot: any) => slot.day === days[0]).sort((a: any, b: any) => a.period_index - b.period_index);
  const isCovered = (day: string, period: number) => sessions.some((session) => session.day === day && session.start_period < period && session.start_period + session.duration_periods > period);
  const teachingSummary = Array.from(sessions.reduce((items: Map<string, Session>, session) => {
    items.set(`${session.semester_number}:${session.course_code}:${session.session_type}`, session);
    return items;
  }, new Map<string, Session>()).values()).sort((left, right) => (left.semester_number || 0) - (right.semester_number || 0) || left.course_code.localeCompare(right.course_code));
  return <article className="official-sheet faculty-sheet">
    <div className="official-grid-wrap">
      <table className="official-grid faculty-grid">
        <caption className="official-header"><div className="official-caption-content"><div className="official-title"><h2>{data.institute_name || "Institute Name"}</h2><h3>FACULTY TIME-TABLE</h3><strong>{facultyCode ? `${facultyCode} · ` : ""}{facultyName}</strong></div><div className="official-meta"><span>{data.academic_year}</span><span>{data.academic_term.toUpperCase()} TERM</span></div></div></caption>
        <thead><tr><th>Time / Day</th>{days.map((day) => <th key={day}>{day}</th>)}</tr></thead>
        <tbody>{periods.map((period: any) => period.blocked ? <tr className="lunch-row" key={period.period_index}><th>{period.start_time} to {period.end_time}</th><td colSpan={days.length}>LUNCH BREAK</td></tr> : <tr key={period.period_index}><th>{period.start_time} to {period.end_time}</th>{days.map((day) => {
          if (isCovered(day, period.period_index)) return null;
          const found = sessions.filter((session) => session.day === day && session.start_period === period.period_index);
          const span = Math.max(1, ...found.map((session) => session.duration_periods));
          return <td key={day} rowSpan={span} className={found.some((session) => session.kind === "lab") ? "practical-cell" : ""}>{found.map((session) => <div className="official-session" key={session.id}><div className="session-heading"><strong>{session.course_code}</strong><small>{session.session_type.toUpperCase()}</small></div><b className="session-name">Semester {roman(session.semester_number || 0)} · {session.course_name}</b><em>{session.room_code}{session.room_name ? ` · ${session.room_name}` : ""}</em></div>)}</td>;
        })}</tr>)}</tbody>
      </table>
    </div>
    <div className="official-footer">
      <table className="scheme-table faculty-summary">
        <thead><tr><th>Semester</th><th>Code & subject</th><th>Activity</th><th>Room</th></tr></thead>
        <tbody>{teachingSummary.map((session) => <tr key={`${session.semester_number}:${session.course_code}:${session.session_type}`}><td>{roman(session.semester_number || 0)}</td><td>{session.course_code} · {session.course_name}</td><td>{session.session_type === "lecture" ? "Lecture / Tutorial" : session.session_type}</td><td>{session.room_code}</td></tr>)}</tbody>
      </table>
    </div>
  </article>;
}
function InstitutionalTimetable({ data, semester }: { data: any; semester: number }) {
  const sessions: Session[] = data.sessions.filter((s: Session) => s.semester_number === semester);
  const semesterInfo = data.semesters.find((s: any) => s.semester_number === semester) || {};
  const configuredDays = new Set(data.time_slots.map((slot: any) => slot.day));
  const days = DAYS.filter((day) => configuredDays.has(day));
  const firstDay = days[0];
  const periods = data.time_slots.filter((slot: any) => slot.day === firstDay).sort((a: any, b: any) => a.period_index - b.period_index);
  const subjects = data.subjects.filter((subject: any) => subject.semester_number === semester);
  const schemeSubjects = Array.from(subjects.reduce((grouped: Map<string, any>, subject: any) => {
    const key = subject.kind === "elective" ? `elective:${subject.elective_group || "semester"}` : `${subject.kind}:${subject.code}:${subject.name}`;
    const existing = grouped.get(key) || {
      ...subject,
      code: subject.kind === "elective" ? "ELECTIVE" : subject.code,
      name: subject.kind === "elective" ? "Elective options" : subject.name,
      lectureHours: 0,
      theoryHours: 0,
      practicalHours: 0,
    };
    if (subject.kind === "lab") {
      existing.practicalHours = Math.max(existing.practicalHours, subject.sessions_per_week * subject.duration_periods);
    } else {
      existing.lectureHours = Math.max(existing.lectureHours, (subject.lecture_sessions_per_week || 0) * subject.duration_periods);
      existing.theoryHours = Math.max(existing.theoryHours, (subject.theory_sessions_per_week || subject.sessions_per_week || 0) * subject.duration_periods);
    }
    grouped.set(key, existing);
    return grouped;
  }, new Map<string, any>()).values()) as any[];
  const isCovered = (day: string, period: number) => sessions.some((s) => s.day === day && s.start_period < period && s.start_period + s.duration_periods > period);
  const totalLecture = schemeSubjects.reduce((sum: number, subject: any) => sum + subject.lectureHours, 0);
  const totalTheory = schemeSubjects.reduce((sum: number, subject: any) => sum + subject.theoryHours, 0);
  const totalPractical = schemeSubjects.reduce((sum: number, subject: any) => sum + subject.practicalHours, 0);
  return (
    <article className="official-sheet">
      <div className="official-grid-wrap">
        <table className="official-grid">
          <caption className="official-header"><div className="official-caption-content"><div className="official-title"><h2>{data.institute_name || "Institute Name"}</h2><h3>Department of {semesterInfo.department_name || "Engineering"}</h3><strong>TIME-TABLE</strong></div><div className="official-meta"><span>Year {Math.ceil(semester / 2)}</span><span>{data.academic_year}</span></div><div className="official-meta"><span>Semester {roman(semester)}</span><span>ROOM NO: {semesterInfo.home_room_code || "-"}</span></div></div></caption>
          <thead><tr><th>Time / Day</th>{days.map((day) => <th key={day}>{day}</th>)}</tr></thead>
          <tbody>{periods.map((period: any) => period.blocked ? (
            <tr className="lunch-row" key={period.period_index}><th>{period.start_time} to {period.end_time}</th><td colSpan={days.length}>LUNCH BREAK</td></tr>
          ) : (
            <tr key={period.period_index}><th>{period.start_time} to {period.end_time}</th>{days.map((day) => {
              if (isCovered(day, period.period_index)) return null;
              const found = sessions.filter((s) => s.day === day && s.start_period === period.period_index);
              const span = Math.max(1, ...found.map((s) => s.duration_periods));
              return <td key={day} rowSpan={span} className={found.some((s) => s.kind === "lab") ? "practical-cell" : ""}><div className="official-session-list">{found.map((s) => <div className="official-session" key={s.id}><div className="session-heading"><strong>{s.course_code}</strong><small>{s.session_type === "lab" ? "LAB" : s.session_type === "lecture" ? "LECTURE/TUTORIAL" : s.kind === "elective" ? "ELECTIVE THEORY" : "THEORY"}</small></div><b className="session-name">{s.course_name}</b>{s.participant_group_ids.some((g) => /B\d|E\d/i.test(g)) && <small className="session-groups">{s.participant_group_ids.map((group) => group.replace(/^SEM-\d+-/i, "")).join(", ")}</small>}<span className="session-faculty">{s.faculty_names?.length ? s.faculty_names.join(", ") : s.faculty_codes.join(", ")}</span><em>{s.room_code}{s.room_name ? ` · ${s.room_name}` : ""}</em></div>)}</div></td>;
            })}</tr>
          ))}</tbody>
        </table>
      </div>
      <div className="official-footer">
        <table className="scheme-table">
          <thead><tr><th>Code</th><th>Subject scheme</th><th>L</th><th>T</th><th>P</th></tr></thead>
          <tbody>
            {schemeSubjects.map((subject: any) => <tr key={`${subject.kind}:${subject.code}:${subject.name}`}><td>{subject.code}</td><td>{subject.name}</td><td>{subject.lectureHours || ""}</td><td>{subject.theoryHours || ""}</td><td>{subject.practicalHours || ""}</td></tr>)}
            <tr className="scheme-total"><th colSpan={2}>Total</th><th>{totalLecture}</th><th>{totalTheory}</th><th>{totalPractical}</th></tr>
          </tbody>
        </table>
      </div>
    </article>
  );
}

function AvailabilityPage({ user }: { user: User }) {
  const optionsQ = useQuery({ queryKey: ["setup-options"], queryFn: setupOptions });
  const [resourceType, setResourceType] = useState<"faculty" | "room">("faculty");
  const [chosenId, setChosenId] = useState<number | null>(null);
  const resources = resourceType === "faculty" ? optionsQ.data?.faculty || [] : optionsQ.data?.rooms || [];
  const selectedId = chosenId ?? resources[0]?.id ?? null;
  const availabilityQ = useQuery({
    queryKey: [resourceType, "availability", selectedId],
    queryFn: () => resourceType === "faculty" ? facultyAvailability(selectedId!) : roomAvailability(selectedId!),
    enabled: !!selectedId,
  });
  const [constraints, setConstraints] = useState<Record<string, { available: boolean; note: string }>>({});
  useEffect(() => {
    setConstraints(Object.fromEntries((availabilityQ.data?.items || []).map((item: any) => [`${item.day}:${item.period_index}`, { available: item.available, note: item.note || "" }])));
  }, [availabilityQ.data]);
  const save = useMutation({
    mutationFn: () => {
      const payload = Object.entries(constraints).map(([key, value]) => {
        const [day, period] = key.split(":");
        return { day, period_index: Number(period), available: value.available, preference: 0, note: value.note };
      });
      return resourceType === "faculty" ? saveFacultyAvailability(selectedId!, payload) : saveRoomAvailability(selectedId!, payload.map(({ preference, ...item }) => item));
    },
  });
  const slots = optionsQ.data?.time_slots || [];
  const periods = Array.from(new Map(slots.map((slot: any) => [slot.period_index, slot])).values()).sort((a: any, b: any) => a.period_index - b.period_index) as any[];
  const days = DAYS.filter((day) => slots.some((slot: any) => slot.day === day));
  const toggle = (key: string) => setConstraints((current) => ({ ...current, [key]: current[key]?.available === false ? { available: true, note: "" } : { available: false, note: current[key]?.note || "" } }));
  const setNote = (key: string, note: string) => setConstraints((current) => ({ ...current, [key]: { available: false, note } }));
  const unavailableCount = Object.values(constraints).filter((item) => !item.available).length;
  const canEdit = user.role === "admin";
  return <section className="page">
    <PageTitle eyebrow="Written hard constraints" title="Faculty and room availability">
      {canEdit && <button className="primary" disabled={!selectedId || save.isPending} onClick={() => save.mutate()}>{save.isPending ? "Saving…" : "Save availability"}</button>}
    </PageTitle>
    <p className="lead">Unavailable periods are hard constraints. Add a written reason such as “department meeting” or “room occupied by another department”; the solver will never allocate that resource in those periods.</p>
    <div className="availability-type-tabs">
      <button className={resourceType === "faculty" ? "active" : ""} onClick={() => { setResourceType("faculty"); setChosenId(null); }}>Faculty</button>
      <button className={resourceType === "room" ? "active" : ""} onClick={() => { setResourceType("room"); setChosenId(null); }}>Rooms & labs</button>
    </div>
    {!resources.length ? <EmptyState text={`Add ${resourceType} records before configuring availability.`} /> : <>
      <div className="card availability-toolbar"><label>{resourceType === "faculty" ? "Teacher" : "Room / laboratory"}<select value={selectedId || ""} onChange={(event) => setChosenId(Number(event.target.value))}>{resources.map((resource: any) => <option key={resource.id} value={resource.id}>{resourceType === "faculty" ? `${resource.faculty_code} · ${resource.name}` : `${resource.code} · ${resource.name}`}</option>)}</select></label><span>{unavailableCount} unavailable period{unavailableCount === 1 ? "" : "s"}</span></div>
      <div className="card table-card availability-grid"><table><thead><tr><th>Time</th>{days.map((day) => <th key={day}>{day}</th>)}</tr></thead><tbody>{periods.map((period: any) => <tr key={period.period_index}><th>{period.start_time}–{period.end_time}</th>{days.map((day) => {const slot = slots.find((item: any) => item.day === day && item.period_index === period.period_index); const key = `${day}:${period.period_index}`; const unavailable = constraints[key]?.available === false; return <td key={day} className={slot?.blocked ? "blocked-slot" : unavailable ? "unavailable-slot" : "available-slot"}>{slot?.blocked ? "Lunch" : <div className="availability-cell"><label className="slot-check"><input disabled={!canEdit} type="checkbox" checked={!unavailable} onChange={() => toggle(key)} /><span>{unavailable ? "Unavailable" : "Available"}</span></label>{unavailable && <input disabled={!canEdit} className="availability-note" placeholder="Written reason" value={constraints[key]?.note || ""} onChange={(event) => setNote(key, event.target.value)} />}</div>}</td>;})}</tr>)}</tbody></table></div>
    </>}
    {save.isSuccess && <div className="validation-ok"><ShieldCheck />Availability and written reasons saved as solver constraints.</div>}
    {(optionsQ.error || availabilityQ.error || save.error) && <div className="error">{errorText(optionsQ.error || availabilityQ.error || save.error)}</div>}
  </section>;
}

function MasterList({ resource, title, user }: { resource: string; title: string; user: User }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: [resource], queryFn: () => list(resource) });
  const options = useQuery({
    queryKey: ["setup-options"],
    queryFn: setupOptions,
  });
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<any | null>(null);
  const canEdit = user.role === "admin";
  const deleting = useMutation({
    mutationFn: (id: number) => remove(resource, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [resource] });
      qc.invalidateQueries({ queryKey: ["setup-options"] });
      qc.invalidateQueries({ queryKey: ["setup-status"] });
    },
  });
  const confirmDelete = (item: any) => {
    const label = item.name || item.code || item.description || `record #${item.id}`;
    if (window.confirm(`Delete ${label}? This cannot be undone.`)) deleting.mutate(item.id);
  };
  const prerequisite =
    resource === "users"
      ? true
      : resource === "faculty"
      ? options.data?.departments.length
      : resource === "rooms"
        ? options.data?.departments.length
        : options.data?.academic_years.length && options.data?.rooms.length;
  const columns = resource === "faculty"
    ? ["faculty_code", "name", "email", "home_department_id", "weekly_limit", "daily_limit", "max_consecutive", "active"]
    : resource === "rooms"
      ? ["code", "name", "department_id", "capacity", "room_type", "features", "concurrent_capacity"]
      : resource === "users"
        ? ["name", "email", "role", "faculty_id", "academic_year_id", "student_group_id", "active"]
      : ["day", "start_period", "duration_periods", "room_id", "faculty_id", "participant_group_id", "description"];
  const columnLabel = (key: string) => ({home_department_id:"department code",department_id:"department code",features:"supported subjects / capabilities",concurrent_capacity:"simultaneous groups",start_period:"start period",duration_periods:"duration",room_id:"room",faculty_id:"faculty",participant_group_id:"student group"} as Record<string,string>)[key] || key.replaceAll("_", " ");
  const cellValue = (key: string, value: any) => {
    if (["home_department_id", "department_id"].includes(key)) return options.data?.departments.find((department: any) => department.id === value)?.code || "—";
    if (key === "room_id") return options.data?.rooms.find((room: any) => room.id === value)?.code || "—";
    if (key === "faculty_id") return options.data?.faculty.find((faculty: any) => faculty.id === value)?.faculty_code || "—";
    if (key === "academic_year_id") return options.data?.academic_years.find((year: any) => year.id === value)?.name || "—";
    if (key === "active") return value ? "Active" : "Inactive";
    return Array.isArray(value) ? value.join(", ") || "—" : String(value ?? "—");
  };
  return (
    <section className="page">
      <PageTitle eyebrow={canEdit ? "Admin master data" : "Read-only directory"} title={title}>
        {canEdit && <button
          className="primary"
          disabled={!prerequisite}
          onClick={() => setAdding(true)}
        >
          Add record
        </button>}
      </PageTitle>
      {!prerequisite && (
        <div className="warning">
          Complete the academic foundation first so this form can use valid
          dropdown options.
        </div>
      )}
      {canEdit && (adding || editing) && options.data && (
        <CreateForm
          resource={resource}
          options={options.data}
          initial={editing}
          close={() => { setAdding(false); setEditing(null); }}
        />
      )}
      {deleting.error && <div className="error">{errorText(deleting.error)}</div>}
      <div className="card table-card">
        {q.isLoading ? (
          "Loading…"
        ) : q.error ? (
          <div className="error">{errorText(q.error)}</div>
        ) : !q.data?.items.length ? (
          <EmptyState text={`No ${title.toLowerCase()} added yet.`} />
        ) : (
          <table>
            <thead>
              <tr>
                {columns.map((key) => <th key={key}>{columnLabel(key)}</th>)}
                {canEdit && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((item: any) => (
                <tr key={item.id}>
                  {columns.map((key) => <td key={key}>{cellValue(key, item[key])}</td>)}
                  {canEdit && <td><div className="record-actions"><button className="icon-button" title="Edit" onClick={() => setEditing(item)}><Pencil size={15} /></button><button className="icon-button danger" title="Delete" onClick={() => confirmDelete(item)}><Trash2 size={15} /></button></div></td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="table-foot">{q.data?.total || 0} records</div>
      </div>
    </section>
  );
}
function CreateForm({
  resource,
  options,
  initial,
  close,
}: {
  resource: string;
  options: any;
  initial?: any;
  close: () => void;
}) {
  const qc = useQueryClient();
  const year = options.academic_years.find((item: any) => item.active) || options.academic_years[0];
  const firstDepartment = options.departments[0];
  const firstRoom = options.rooms[0];
  const defaults: any =
    resource === "faculty"
      ? {
          faculty_code: "",
          name: "",
          email: "",
          home_department_id: firstDepartment?.id,
          weekly_limit: 18,
          daily_limit: 6,
          max_consecutive: 3,
          active: true,
        }
      : resource === "rooms"
        ? {
            code: "",
            name: "",
            department_id: firstDepartment?.id,
            capacity: 60,
            room_type: "theory",
            features: [],
            concurrent_capacity: 1,
          }
        : resource === "users"
          ? {
              name: "",
              email: "",
              password: "",
              role: "student",
              faculty_id: null,
              academic_year_id: year?.id,
              student_group_id: options.student_groups?.[0] || "",
              active: true,
            }
        : {
            academic_year_id: year?.id,
            day: "Monday",
            start_period: 0,
            duration_periods: 2,
            room_id: firstRoom?.id,
            faculty_id: null,
            participant_group_id: "FIRST-YEAR-EE",
            description: "",
          };
  const editable = initial ? Object.fromEntries(Object.keys(defaults).map((key) => [key, initial[key] ?? defaults[key]])) : defaults;
  const [form, setForm] = useState<any>(editable);
  const [capabilitiesText, setCapabilitiesText] = useState(
    (editable.features || []).join("\n"),
  );
  const mutation = useMutation({
    mutationFn: () => {
      const payload = resource === "rooms"
        ? { ...form, features: splitCapabilities(capabilitiesText) }
        : resource === "users" && initial && !form.password
          ? { ...form, password: null }
          : form;
      return initial ? update(resource, initial.id, payload) : create(resource, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [resource] });
      qc.invalidateQueries({ queryKey: ["setup-options"] });
      qc.invalidateQueries({ queryKey: ["setup-status"] });
      close();
    },
  });
  const fields = Object.keys(defaults);
  function updateField(key: string, value: string) {
    const numeric = [
      "home_department_id",
      "weekly_limit",
      "daily_limit",
      "max_consecutive",
      "department_id",
      "capacity",
      "concurrent_capacity",
      "academic_year_id",
      "start_period",
      "duration_periods",
      "room_id",
      "faculty_id",
    ];
    setForm({
      ...form,
      [key]: numeric.includes(key)
        ? value === "" ? null : Number(value)
        : value,
    });
  }
  return (
    <Modal
      title={`${initial ? "Edit" : "Add"} ${resource.replace("rooms", "room").replace("reservations", "reservation")}`}
      close={close}
      submit={() => mutation.mutate()}
      pending={mutation.isPending}
      error={mutation.error}
    >
      {fields.map((key) => (
        <label key={key}>
          {key === "features" ? "Supported subjects / capabilities" : key === "concurrent_capacity" ? "Maximum simultaneous groups" : key.replaceAll("_", " ")}
          {["home_department_id", "department_id"].includes(key) ? (
            <select
              value={form[key]}
              onChange={(e) => updateField(key, e.target.value)}
            >
              {options.departments.map((d: any) => (
                <option key={d.id} value={d.id}>
                  {d.code} · {d.name}
                </option>
              ))}
            </select>
          ) : key === "role" ? (
            <select value={form[key]} onChange={(e) => updateField(key, e.target.value)}>
              <option value="admin">Administrator</option>
              <option value="faculty">Faculty</option>
              <option value="student">Student</option>
            </select>
          ) : key === "active" ? (
            <label className="checkbox"><input type="checkbox" checked={!!form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} /> {resource === "faculty" ? "Faculty active" : "Account enabled"}</label>
          ) : key === "academic_year_id" ? (
            <select
              disabled={resource === "users" && form.role !== "student"}
              value={form[key]}
              onChange={(e) => updateField(key, e.target.value)}
            >
              {options.academic_years.map((y: any) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </select>
          ) : key === "room_id" ? (
            <select
              value={form[key]}
              onChange={(e) => updateField(key, e.target.value)}
            >
              {options.rooms.map((r: any) => (
                <option key={r.id} value={r.id}>
                  {r.code} · {r.name}
                </option>
              ))}
            </select>
          ) : key === "faculty_id" ? (
            <select disabled={resource === "users" && form.role !== "faculty"} value={form[key] || ""} onChange={(e) => updateField(key, e.target.value)}>
              <option value="">{resource === "users" ? "Select linked faculty" : "No faculty-specific block"}</option>
              {options.faculty.map((faculty: any) => <option key={faculty.id} value={faculty.id}>{faculty.faculty_code} · {faculty.name}</option>)}
            </select>
          ) : key === "student_group_id" ? (
            <select disabled={resource === "users" && form.role !== "student"} value={form[key] || ""} onChange={(e) => updateField(key, e.target.value)}>
              <option value="">Select semester or batch</option>
              {(options.student_groups || []).map((group: string) => <option key={group} value={group}>{group}</option>)}
            </select>
          ) : key === "room_type" ? (
            <select
              value={form[key]}
              onChange={(e) => updateField(key, e.target.value)}
            >
              <option value="theory">Theory</option>
              <option value="lab">Laboratory</option>
            </select>
          ) : key === "day" ? (
            <select
              value={form[key]}
              onChange={(e) => updateField(key, e.target.value)}
            >
              {DAYS.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          ) : key === "features" ? (
            <textarea
              placeholder={"One per line, or separated by commas/semicolons\nExample: Network Lab; Electrical Machines"}
              value={capabilitiesText}
              onChange={(e) => setCapabilitiesText(e.target.value)}
            />
          ) : (
            <input
              required={!["features", "faculty_id", "participant_group_id"].includes(key) && !(resource === "users" && !!initial && key === "password")}
              type={
                typeof form[key] === "number"
                  ? "number"
                  : key === "password"
                    ? "password"
                  : key === "email"
                    ? "email"
                    : "text"
              }
              value={
                Array.isArray(form[key])
                  ? form[key].join(", ")
                  : (form[key] ?? "")
              }
              placeholder={key === "email" ? "name@sgsits.ac.in" : key === "student_group_id" ? "SEM-3 or SEM-3-B1" : undefined}
              onChange={(e) => updateField(key, e.target.value)}
            />
          )}
        </label>
      ))}
    </Modal>
  );
}
function Analytics() {
  const q = useQuery({
    queryKey: ["analytics"],
    queryFn: () => request<any>("/analytics/summary"),
  });
  return (
    <section className="page">
      <PageTitle eyebrow="Quality and operations" title="Analytics" />
      <div className="metric-grid">
        <Metric
          label="Successful runs"
          value={String(q.data?.successful_runs ?? 0)}
          detail="Recent runs"
          icon={<ShieldCheck />}
        />
        <Metric
          label="Engine"
          value="CP-SAT"
          detail="Hybrid refinement"
          icon={<Settings />}
        />
      </div>
      <div className="card table-card">
        <h3>Recent generation runs</h3>
        {q.data?.recent_runs?.length ? (
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Mode</th>
                <th>Runtime</th>
                <th>Objective</th>
              </tr>
            </thead>
            <tbody>
              {q.data.recent_runs.map((r: any) => (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>
                    <span className="badge">{r.status}</span>
                  </td>
                  <td>{r.mode}</td>
                  <td>{r.runtime?.toFixed(3)}s</td>
                  <td>{r.objective}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState text="No generation runs yet." />
        )}
      </div>
    </section>
  );
}
function DownloadPage() {
  return (
    <section className="page">
      <PageTitle eyebrow="Generated timetable" title="Download" />
      <div className="card download-card">
        <Download />
        <h2>Export current timetable</h2>
        <button className="primary" onClick={downloadCsv}>
          Download CSV
        </button>
      </div>
    </section>
  );
}
