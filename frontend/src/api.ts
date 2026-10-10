export type User = {
  id: number;
  email: string;
  name: string;
  role: "admin" | "faculty" | "student";
  faculty_id?: number;
  student_group_id?: string;
};
export type Session = {
  id: number;
  course_offering_id: number;
  course_code: string;
  course_name: string;
  kind: string;
  semester_number: number | null;
  day: string;
  start_period: number;
  duration_periods: number;
  room_id: number;
  room_code: string;
  faculty_ids: number[];
  faculty_names: string[];
  faculty_codes: string[];
  participant_group_ids: string[];
};
export type TimetableData = {
  id: number;
  version: number;
  status: string;
  institute_name: string;
  academic_year: string;
  academic_term: "odd" | "even";
  semesters: any[];
  subjects: any[];
  time_slots: any[];
  sessions: Session[];
};
export type SetupStatus = {
  counts: Record<string, number>;
  steps: { key: string; label: string; complete: boolean }[];
  ready_for_validation: boolean;
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
export const login = (email: string, password: string) =>
  request<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
export const bootstrapStatus = () =>
  request<{ needs_admin: boolean }>("/auth/bootstrap-status");
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
export const timetable = () => request<TimetableData>("/timetables/latest");
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
export const facultyAvailability = (facultyId: number) =>
  request<{ items: any[] }>(`/faculty/${facultyId}/availability`);
export const saveFacultyAvailability = (facultyId: number, slots: any[]) =>
  request<{ items: any[] }>(`/faculty/${facultyId}/availability`, {
    method: "PUT",
    body: JSON.stringify(slots),
  });
export const offerings = (semesterId: number) =>
  request<{ items: any[] }>(
    `/setup/course-offerings?semester_offering_id=${semesterId}`,
  );
export const addOffering = (data: any) =>
  request("/setup/course-offerings", {
    method: "POST",
    body: JSON.stringify(data),
  });
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
