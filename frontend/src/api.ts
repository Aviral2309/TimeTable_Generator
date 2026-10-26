export type User = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "faculty" | "student";
  faculty_id?: number;
  academic_year_id?: number;
  student_group_id?: string;
  active?: boolean;
};
export type Session = {
  id: number;
  course_offering_id: number;
  course_code: string;
  course_name: string;
  kind: string;
  session_type: "theory" | "lecture" | "lab";
  semester_number: number | null;
  day: string;
  start_period: number;
  duration_periods: number;
  room_id: number;
  room_code: string;
  room_name: string;
  faculty_ids: number[];
  faculty_names: string[];
  faculty_codes: string[];
  participant_group_ids: string[];
};
export type TimetableData = {
  id: number;
  version: number;
  status: string;
  created_at?: string;
  academic_year_id: number;
  institute_name: string;
  academic_year: string;
  academic_term: "odd" | "even";
  semesters: any[];
  subjects: any[];
  time_slots: any[];
  sessions: Session[];
};
export type RescheduleRequest = {
  source_timetable_id: number;
  resource_type: "faculty" | "room";
  resource_id: number;
  day: string;
  start_period: number;
  duration_periods: number;
  reason: string;
  time_limit_seconds: number;
  random_seed: number;
};
export type ReschedulePlan = {
  source_timetable_id: number;
  source_version: number;
  result_timetable_id?: number;
  result_version?: number;
  event_id?: number;
  status: string;
  valid: boolean;
  resource_name: string;
  affected_sessions: number;
  moved_sessions: number;
  changes: Array<{
    session_id: string;
    course_code: string;
    course_name: string;
    semester_number: number;
    kind: string;
    participant_group_ids: string[];
    before: { day: string; start_period: number; duration_periods: number; room_id: number; room_code: string };
    after: { day: string; start_period: number; duration_periods: number; room_id: number; room_code: string };
  }>;
  diagnostics: Array<{ code?: string; message?: string }>;
  metrics: Record<string, number>;
};
export type SetupStatus = {
  counts: Record<string, number>;
  steps: { key: string; label: string; complete: boolean }[];
  ready_for_validation: boolean;
  readiness_issues: Array<{ code: string; message: string }>;
  active_year: { id: number; name: string; term_type: "odd" | "even" } | null;
};
const API = "/api";
export const token = () => localStorage.getItem("timetable_token");
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (response.status === 401) {
    localStorage.removeItem("timetable_token");
    localStorage.removeItem("timetable_user");
    window.dispatchEvent(new Event("timetable:unauthorized"));
  }
  if (!response.ok) {
    let detail: any = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail),
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export async function downloadDatabase(kind: "backup" | "starter") {
  const endpoint = kind === "backup" ? "database-backup" : "starter-database";
  const response = await fetch(`${API}/deployment/${endpoint}`, {
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
  });
  if (!response.ok) {
    let detail = `Download failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] || `sgsits-timetable-${kind}.db`;
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
export async function restoreDatabase(file: File) {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API}/deployment/restore-database`, {
    method: "POST",
    headers: token() ? { Authorization: `Bearer ${token()}` } : {},
    body,
  });
  if (!response.ok) {
    let detail = `Restore failed (${response.status})`;
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json();
}
export const login = (email: string, password: string, role: User["role"]) =>
  request<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, role }),
  });
export type RegistrationOptions = {
  faculty: Array<{ id: number; faculty_code: string; name: string }>;
  academic_years: Array<{ id: number; name: string; term_type: "odd" | "even"; semesters: Array<{ semester_number: number; groups: string[] }> }>;
};
export const registrationOptions = () => request<RegistrationOptions>("/auth/registration-options");
export const registerAccount = (data: Record<string, unknown>) =>
  request<{ pending_approval: boolean; message?: string; access_token?: string; user?: User }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const changePassword = (currentPassword: string, newPassword: string) =>
  request<{ message: string }>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
export const bootstrapStatus = () =>
  request<{ needs_admin: boolean; has_department_data: boolean }>("/auth/bootstrap-status");
export const bootstrapAdmin = (data: {
  name: string;
  email: string;
  password: string;
}) =>
  request<{ access_token: string; user: User }>("/auth/bootstrap", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const list = (resource: string) =>
  request<{ items: any[]; total: number }>(`/${resource}?page=1&page_size=100`);
export const create = (resource: string, data: unknown) =>
  request(`/${resource}`, { method: "POST", body: JSON.stringify(data) });
export const update = (resource: string, id: number, data: unknown) =>
  request(`/${resource}/${id}`, { method: "PUT", body: JSON.stringify(data) });
export const remove = (resource: string, id: number) =>
  request(`/${resource}/${id}`, { method: "DELETE" });
export const timetable = (id?: number) => request<TimetableData>(id ? `/timetables/${id}` : "/timetables/latest");
export const timetableValidation = (id: number) => request<any>(`/timetables/${id}/validation`);
export const timetableHistory = (academicYearId?: number) =>
  request<{ items: any[] }>(`/timetables${academicYearId ? `?academic_year_id=${academicYearId}` : ""}`);
export const setTimetableStatus = (id: number, status: "draft" | "published" | "archived") =>
  request<{ id: number; version: number; status: string }>(`/timetables/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
export const timetableBackups = () =>
  request<{ items: any[] }>("/timetable-backups");
export const timetableBackup = (id: number) =>
  request<any>(`/timetable-backups/${id}`);
export const previewReschedule = (data: RescheduleRequest) =>
  request<ReschedulePlan>("/rescheduling/preview", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const applyReschedule = (data: RescheduleRequest) =>
  request<ReschedulePlan>("/rescheduling/apply", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const rescheduleHistory = () =>
  request<{ items: any[] }>("/rescheduling/history");
export const setupOptions = () => request<any>("/setup/options");
export const setupStatus = () => request<SetupStatus>("/setup/status");
export const setupCreate = (resource: string, data: unknown) =>
  request(`/setup/${resource}`, { method: "POST", body: JSON.stringify(data) });
export const setupUpdate = (resource: string, id: number, data: unknown) =>
  request(`/setup/${resource}/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const setupRemove = (resource: string, id: number) =>
  request(`/setup/${resource}/${id}`, { method: "DELETE" });
export const semesters = (academicYearId: number) =>
  request<{ items: any[] }>(
    `/setup/semesters?academic_year_id=${academicYearId}`,
  );
export const setupUpdateRoot = (resource: string, data: unknown) =>
  request(`/setup/${resource}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const setupRemoveRoot = (resource: string) =>
  request(`/setup/${resource}`, { method: "DELETE" });
export const loadDemoData = (termType: "odd" | "even") =>
  request<any>("/setup/demo-data", {
    method: "POST",
    body: JSON.stringify({ term_type: termType }),
  });
export const createTermCohorts = (data: { academic_year_id: number; department_id: number; default_strength: number }) =>
  request<{ items: any[] }>("/setup/term-cohorts", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const facultyAvailability = (facultyId: number) =>
  request<{ items: any[] }>(`/faculty/${facultyId}/availability`);
export const saveFacultyAvailability = (facultyId: number, slots: any[]) =>
  request<{ items: any[] }>(`/faculty/${facultyId}/availability`, {
    method: "PUT",
    body: JSON.stringify(slots),
  });
export const roomAvailability = (roomId: number) =>
  request<{ items: any[] }>(`/rooms/${roomId}/availability`);
export const saveRoomAvailability = (roomId: number, slots: any[]) =>
  request<{ items: any[] }>(`/rooms/${roomId}/availability`, {
    method: "PUT",
    body: JSON.stringify(slots),
  });
export const academicTerms = () => request<{ items: any[] }>("/setup/academic-years");
export const activateAcademicTerm = (id: number) =>
  request<any>(`/setup/academic-years/${id}/activate`, { method: "POST" });
export const offerings = (semesterId: number) =>
  request<{ items: any[] }>(
    `/setup/course-offerings?semester_offering_id=${semesterId}`,
  );
export const addOffering = (data: any) =>
  request("/setup/course-offerings", {
    method: "POST",
    body: JSON.stringify(data),
  });
export const addLabBatchOfferings = (data: any) =>
  request<{ items: any[]; batch_count: number; elective_lab: boolean }>(
    "/setup/course-offerings/lab-batches",
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  );
export const updateOffering = (id: number, data: any) =>
  request(`/setup/course-offerings/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
export const removeOffering = (id: number) =>
  request(`/setup/course-offerings/${id}`, { method: "DELETE" });
export const validateSetup = (academicYearId: number, ids: number[]) =>
  request<{ valid: boolean; errors: any[] }>(
    `/setup/validate?academic_year_id=${academicYearId}`,
    { method: "POST", body: JSON.stringify(ids) },
  );
